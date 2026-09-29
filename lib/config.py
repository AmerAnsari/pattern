#!/usr/bin/env python3
"""Config resolution, paths, and model availability.

Resolution is project config over shipped defaults, nothing else — the data a
project learns and the settings it learns under both stay inside that project.

Also owns the model probe. The default model is Opus; if it isn't available we
do not quietly fall back to something cheaper, because a profile distilled by a
weaker model is worse than no profile and the user would never be told. Instead
auto-capture pauses and asks to be configured.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

CONFIG_RELPATH = Path(".patternscribe") / "config.json"

# The runner is a separate program that can send data off the machine, so it is
# given only what it needs to start — not a copy of the whole environment, and
# deliberately no credential. A secret this plugin never passes on cannot be
# leaked by it, by accident or otherwise.
#
# Nothing here authenticates anything: these are paths, locale and proxy
# settings. The runner finds its own credentials the way it normally does, from
# its own configuration or keychain, which it reaches through HOME.
RUNNER_ENV_KEYS = (
    "PATH", "HOME", "USER", "LOGNAME", "SHELL", "TMPDIR", "LANG", "LC_ALL",
    "TERM", "SystemRoot", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "ComSpec",
    "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "no_proxy",
    "SSL_CERT_FILE", "SSL_CERT_DIR", "NODE_EXTRA_CA_CERTS",
    "XDG_CONFIG_HOME", "XDG_CACHE_HOME",
)

# Only this plugin's own variables are forwarded by prefix. If a runner needs a
# credential from the environment, the user names it in `runner.pass_env`
# themselves — this plugin never decides on its own which of their secrets to
# hand to a program that talks to the network.
RUNNER_ENV_PREFIXES = ("PATTERNSCRIBE_",)

PROBE_TTL_SECONDS = 30 * 24 * 3600
PROBE_TIMEOUT_SECONDS = 90
PROBE_BUDGET_USD = "0.10"

# "budget exceeded" means the model answered and we cut it off — that is a
# successful probe. Only a refusal to run the model at all counts as a miss.
PROBE_OK = ("budget",)
PROBE_MISS = ("not found", "not available", "unavailable", "does not exist",
             "invalid model", "unknown model", "not authorized", "access denied",
             "permission", "unauthorized")


def runner_env(config: dict | None = None, **extra: str) -> dict:
    """The environment handed to the runner: an allowlist, plus `extra`.

    `runner.pass_env` lets the user name variables to forward as well. It is
    empty by default, so out of the box no credential of theirs reaches the
    runner through this plugin. Someone whose runner authenticates from the
    environment rather than a keychain opts in explicitly, naming the variable
    they chose to share.
    """
    allowed = set(RUNNER_ENV_KEYS)
    for name in ((config or {}).get("runner", {}).get("pass_env") or []):
        if isinstance(name, str) and name.strip():
            allowed.add(name.strip())

    env = {
        key: value
        for key, value in os.environ.items()
        if key in allowed or key.startswith(RUNNER_ENV_PREFIXES)
    }
    env.update(extra)
    return env


def plugin_root() -> Path:
    return Path(__file__).resolve().parent.parent


def project_root(start: str | Path | None = None) -> Path:
    """Nearest enclosing git repo, else the directory we were handed."""
    current = Path(start or os.environ.get("PATTERNSCRIBE_CWD") or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    return current


def slug(path: Path) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", str(path)).strip("-")


def load(root: Path | None = None) -> dict:
    root = root or project_root()
    config = json.loads((plugin_root() / "config.default.json").read_text(encoding="utf-8"))

    # The override always lives at this fixed path, even when `data_dir` points
    # the learned files somewhere else — otherwise finding the config would
    # require already having read it.
    override_path = root / CONFIG_RELPATH
    if override_path.is_file():
        try:
            override = json.loads(override_path.read_text(encoding="utf-8"))
        except ValueError as exc:
            print(f"patternscribe: ignoring malformed {override_path}: {exc}", file=sys.stderr)
            override = {}
        runner = {**config.get("runner", {}), **override.pop("runner", {})}
        config.update(override)
        config["runner"] = runner

    return config


def data_dir(config: dict, root: Path | None = None) -> Path:
    root = root or project_root()
    raw = str(config.get("data_dir") or ".patternscribe").replace("{slug}", slug(root))
    path = Path(raw).expanduser()
    return path if path.is_absolute() else root / path


def state_dir(config: dict, root: Path | None = None) -> Path:
    return data_dir(config, root) / "state"


def _probe_cache(config: dict, root: Path | None) -> Path:
    return state_dir(config, root) / "model-probe.json"


def _read_probe(path: Path) -> dict:
    try:
        cached = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if time.time() - cached.get("at", 0) > PROBE_TTL_SECONDS:
        return {}
    return cached


def resolve_model(config: dict, root: Path | None = None, allow_probe: bool = True):
    """Return (model, reason). model is None when nothing usable was found.

    `allow_probe=False` reads the cache only — session-start must never block a
    session on a network call.
    """
    runner = config.get("runner", {})
    configured = runner.get("model")
    if configured:
        return configured, "configured"

    cache_path = _probe_cache(config, root)
    cached = _read_probe(cache_path)
    if cached.get("model"):
        return cached["model"], "probed"
    if cached and not cached.get("model"):
        return None, "probe found no available model"
    if not allow_probe:
        return None, "not probed yet"

    command = runner.get("command", "claude")
    for candidate in runner.get("model_probe") or ["opus"]:
        if _model_works(command, candidate, config):
            _write_probe(cache_path, candidate)
            return candidate, "probed"

    _write_probe(cache_path, None)
    return None, "probe found no available model"


def _model_works(command: str, model: str, config: dict | None = None) -> bool:
    """Ask the runner for one word and see whether the model answers at all."""
    try:
        result = subprocess.run(
            # --no-session-persistence matters: a probe that leaves a transcript
            # behind is later picked up as an unanalysed session.
            [command, "-p", "--model", model, "--no-session-persistence",
             "--max-budget-usd", PROBE_BUDGET_USD, "reply with: ok"],
            capture_output=True,
            text=True,
            timeout=PROBE_TIMEOUT_SECONDS,
            env=runner_env(config, PATTERNSCRIBE_DISTILL="1"),
        )
    except (OSError, subprocess.SubprocessError):
        return False

    if result.returncode == 0 and result.stdout.strip():
        return True

    message = f"{result.stdout} {result.stderr}".lower()
    if any(token in message for token in PROBE_MISS):
        return False
    # Spending the cap is proof the model was reachable.
    return any(token in message for token in PROBE_OK)


def _write_probe(path: Path, model: str | None) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"model": model, "at": time.time()}, indent=2), encoding="utf-8")
    except OSError:
        pass


def main() -> int:
    args = sys.argv[1:]
    root = project_root()
    config = load(root)

    if not args or args[0] == "show":
        model, reason = resolve_model(config, root, allow_probe=False)
        print(f"project root : {root}")
        print(f"data dir     : {data_dir(config, root)}")
        print(f"enabled      : {config.get('enabled')}")
        print(f"superpowers  : {config.get('use_superpowers')}")
        print(f"runner       : {config['runner'].get('command')}")
        print(f"model        : {model or '(unresolved)'} ({reason})")
        print(f"budget       : ${config.get('budget_usd')} per run")
        print(f"min signal   : {config.get('min_signal')}")
        return 0

    if args[0] == "json":
        print(json.dumps(config, indent=2))
        return 0

    if args[0] == "get":
        node = config
        for part in args[1].split("."):
            node = node.get(part) if isinstance(node, dict) else None
        print("" if node is None else (node if isinstance(node, str) else json.dumps(node)))
        return 0

    if args[0] == "path":
        target = args[1] if len(args) > 1 else "data"
        print({"data": data_dir(config, root), "state": state_dir(config, root),
               "root": root, "plugin": plugin_root()}[target])
        return 0

    if args[0] == "resolve-model":
        model, reason = resolve_model(config, root, allow_probe="--no-probe" not in args)
        print(model or "")
        print(reason, file=sys.stderr)
        return 0 if model else 1

    print(f"pattern: unknown config command: {args[0]}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
