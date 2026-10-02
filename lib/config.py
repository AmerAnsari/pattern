#!/usr/bin/env python3
"""Config resolution and paths.

Resolution is project config over shipped defaults, nothing else — the data a
project learns and the settings it learns under both stay inside that project.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

CONFIG_RELPATH = Path(".patternscribe") / "config.json"


def plugin_root() -> Path:
    return Path(__file__).resolve().parent.parent


def project_root(start: str | Path | None = None) -> Path:
    """Nearest enclosing git repo, else the directory we were handed."""
    current = Path(start or Path.cwd()).resolve()
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
        config.update(override)

    return config


def data_dir(config: dict, root: Path | None = None) -> Path:
    root = root or project_root()
    raw = str(config.get("data_dir") or ".patternscribe").replace("{slug}", slug(root))
    path = Path(raw).expanduser()
    return path if path.is_absolute() else root / path


def main() -> int:
    args = sys.argv[1:]
    root = project_root()
    config = load(root)

    if not args or args[0] == "show":
        print(f"project root : {root}")
        print(f"data dir     : {data_dir(config, root)}")
        print(f"superpowers  : {config.get('use_superpowers')}")
        print(f"decay after  : {config.get('decay_sessions')} sessions")
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
        print({"data": data_dir(config, root), "root": root, "plugin": plugin_root()}[target])
        return 0

    print(f"patternscribe: unknown config command: {args[0]}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
