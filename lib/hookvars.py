#!/usr/bin/env python3
"""Read a hook's JSON payload on stdin and print the requested fields.

Hooks receive JSON and are written in shell, and the payload's fields can be
missing or oddly typed. Doing the parsing here keeps the hook scripts readable and
means a malformed payload yields empty values rather than a crash during
someone's session exit.

One value per line, in the order asked for, so the caller can read them
positionally:

    printf '%s' "$PAYLOAD" | hookvars.py session_id cwd
    -> a line holding the session id, then a line holding the cwd

Nothing here is meant to be evaluated as shell. The caller reads the lines with
`read`, so a payload field can never be executed however it is spelled. Newlines
inside a value are collapsed to spaces, because one stray newline would
otherwise shift every later field onto the wrong variable.
"""

import json
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
        print(" ".join(value.split("\n")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
