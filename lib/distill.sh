#!/usr/bin/env bash
# Hand one session's digest to the configured runner and let it update the profile.
#
# Runs detached from the session that produced the digest — by the time this
# starts, that session is usually gone. Everything it needs is on disk.
#
# Usage: distill.sh <digest-file> [session-id]
set -uo pipefail

LIB="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN="$(dirname "$LIB")"
DIGEST="${1:?usage: distill.sh <digest-file> [session-id]}"
SESSION_ID="${2:-}"

ROOT="$(PATTERNSCRIBE_CWD="${PATTERNSCRIBE_CWD:-$PWD}" python3 "$LIB/config.py" path root)"
DATA="$(PATTERNSCRIBE_CWD="$ROOT" python3 "$LIB/config.py" path data)"
STATE="$DATA/state"
LOG="$STATE/distill.log"

mkdir -p "$STATE"
log() { printf '[%s] %s\n' "$(date +%FT%T)" "$*" >> "$LOG"; }
cleanup() { rmdir "$STATE/lock" 2>/dev/null || true; }
trap cleanup EXIT

log "start session=${SESSION_ID:-?} digest=$DIGEST"

MODEL="$(PATTERNSCRIBE_CWD="$ROOT" python3 "$LIB/config.py" resolve-model 2>>"$LOG")"
if [ -z "$MODEL" ]; then
  log "no usable model — pausing until configured"
  printf 'pattern: no usable model. Set runner.model in %s/.patternscribe/config.json\n' "$ROOT" \
    > "$STATE/needs-config"
  exit 0
fi

PATTERNSCRIBE_CWD="$ROOT" python3 - "$PLUGIN" "$ROOT" "$DATA" "$DIGEST" "$MODEL" "$SESSION_ID" <<'PY' >> "$LOG" 2>&1
import json, os, subprocess, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1]) / "lib"))
import config as cfg  # noqa: E402

plugin, root, data, digest, model, session_id = (
    Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]),
    sys.argv[5], sys.argv[6],
)
conf = cfg.load(root)
runner = conf.get("runner", {})
patterns = data / "PATTERNS.md"

# Conventions the project already states out loud; the profile must not echo them.
known = [n for n in ("CLAUDE.md", "AGENTS.md", "GEMINI.md", ".cursorrules") if (root / n).is_file()]
known += [str(p.relative_to(root)) for p in sorted(root.glob(".claude/skills/*/SKILL.md"))]
context = ", ".join(f"`{n}`" for n in known) if known else "(none in this project)"

prompt = (plugin / "prompts" / "distill.md").read_text(encoding="utf-8")
prompt = (prompt
          .replace("{patterns_file}", str(patterns))
          .replace("{digest_file}", str(digest))
          .replace("{journal_file}", str(data / "journal.md"))
          .replace("{last_learned_file}", str(data / "state" / "last-learned.md"))
          .replace("{decay_sessions}", str(conf.get("decay_sessions", 10)))
          .replace("{context_files}", context))

if not runner.get("writes_files", True):
    # The runner can only talk, so ask for the whole file back and write it here.
    prompt += (
        "\n\n## Output\n\nYou cannot edit files. Print the complete new contents of the "
        "profile and nothing else — no fences, no commentary. Ignore the instructions "
        "above about writing to the journal and the last-learned file.\n\n"
        "Current profile:\n\n" + patterns.read_text(encoding="utf-8")
        + "\n\nSession digest:\n\n" + digest.read_text(encoding="utf-8")
    )

fields = {
    "{model}": model,
    "{budget}": str(conf.get("budget_usd", 0.30)),
    "{data_dir}": str(data),
    "{prompt_file}": "",
    "{digest_file}": str(digest),
    "{patterns_file}": str(patterns),
}

prompt_file = None
if runner.get("prompt") == "file":
    handle = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
    handle.write(prompt)
    handle.close()
    prompt_file = handle.name
    fields["{prompt_file}"] = prompt_file

argv = [runner.get("command", "claude")]
for arg in runner.get("args", []):
    for token, value in fields.items():
        arg = arg.replace(token, value)
    argv.append(arg)

stdin_text = None
if runner.get("prompt") == "stdin":
    stdin_text = prompt
elif runner.get("prompt") != "file":
    argv.append(prompt)

env = cfg.runner_env(PATTERNSCRIBE_DISTILL="1", PATTERNSCRIBE_CWD=str(root))
# Log the shape of the command, never the prompt itself.
shown = " ".join(a if len(a) < 40 else a[:37] + "…" for a in argv[:8])
print(f"runner: {shown}  ({len(argv)} args, prompt {len(prompt)} chars)")

try:
    result = subprocess.run(
        argv, input=stdin_text, capture_output=True, text=True,
        timeout=runner.get("timeout_seconds", 300), cwd=root, env=env,
    )
except subprocess.TimeoutExpired:
    print("runner timed out")
    sys.exit(1)
except OSError as exc:
    print(f"runner failed to start: {exc}")
    sys.exit(1)
finally:
    if prompt_file:
        os.unlink(prompt_file)

if result.returncode != 0:
    detail = (result.stderr.strip() or result.stdout.strip())[:500]
    print(f"runner exited {result.returncode}: {detail or '(no output)'}")
    sys.exit(1)

if not runner.get("writes_files", True):
    body = result.stdout.strip()
    if not body.startswith("#"):
        print("runner returned something that is not a profile; leaving the file alone")
        print(body[:300])
        sys.exit(1)
    patterns.write_text(body + "\n", encoding="utf-8")
    print("profile written from runner stdout")

print(result.stdout.strip()[-400:] or "(no output)")
PY
STATUS=$?

if [ "$STATUS" -eq 0 ]; then
  if [ -n "$SESSION_ID" ]; then
    printf '%s\n' "$SESSION_ID" > "$STATE/last-session"
    # The ledger is what stops a session being counted twice. Confidence counts
    # are only meaningful if each session contributes to them once.
    printf '%s\n' "$SESSION_ID" >> "$STATE/analyzed"
  fi
  rm -f "$DIGEST" "$STATE/needs-config"
  log "done"
else
  log "failed (status $STATUS) — re-queueing"
  [ -n "$SESSION_ID" ] && printf '%s\n' "$SESSION_ID" >> "$STATE/queue"
fi

# Anything that arrived while the lock was held gets picked up by the next
# session-start, which re-queues unanalysed transcripts anyway.
exit 0
