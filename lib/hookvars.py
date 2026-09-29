#!/usr/bin/env python3
"""Turn a hook's JSON payload on stdin into shell assignments on stdout.

Hooks receive JSON and are written in shell, and every host spells the fields
slightly differently. Doing the parsing here keeps the hook scripts readable
and means a malformed payload produces empty variables rather than a crash
during someone's session exit.

    eval "$(hookvars.py session_id transcript_path cwd < payload.json)"
    -> HOOK_SESSION_ID='…'  HOOK_TRANSCRIPT_PATH='…'  HOOK_CWD='…'
"""

import json
import shlex
import sys

ALIASES = {
    "session_id": ("session_id", "sessionId", "id"),
    "transcript_path": ("transcript_path", "transcriptPath", "transcript"),
    "cwd": ("cwd", "workspace", "workspacePath", "projectPath"),
    "reason": ("reason", "source", "trigger"),
}


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}

    for key in sys.argv[1:] or list(ALIASES):
        value = ""
        for alias in ALIASES.get(key, (key,)):
            candidate = data.get(alias)
            if candidate:
                value = str(candidate)
                break
        print(f"HOOK_{key.upper()}={shlex.quote(value)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
