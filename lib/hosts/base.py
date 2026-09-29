"""Host adapter interface.

Only *automatic* session-end capture needs to understand a host's transcript
format. Everything else in this plugin (the skill, the commands) works on any
host, because the live agent can reflect on the conversation it is already in.

To support a new host, add a module next to this one exposing the same four
functions and register it in `registry` below. A host with no adapter loses
only the unattended capture; `/patternscribe doctor` reports that plainly.

An adapter normalises transcript records into this shape:

    {
      "ts":         str,          # ISO timestamp, may be ""
      "role":       str,          # "user" | "assistant"
      "text":       str,          # plain text of the message, may be ""
      "feedback":   str | None,   # explicit correction the user typed at a prompt
      "denial":     str | None,   # how the user refused an action, if they did
      "tools":      list[dict],   # [{"name": str, "summary": str}] - names/args only
      "tool_error": bool,         # a tool call came back as an error
      "sidechain":  bool,         # produced by a subagent rather than the main thread
    }

Adapters must never emit tool *output*, file contents, or anything they have
not deliberately summarised. Everything an adapter yields ends up in a digest
that is handed to a model.
"""

from __future__ import annotations

import importlib

# Keys whose values are safe to summarise from a tool call. Anything not listed
# here is dropped, so a Write's file body or a fetched page never leaks into a
# digest just because a new tool appeared.
SAFE_ARG_KEYS = (
    "file_path",
    "path",
    "command",
    "pattern",
    "glob",
    "url",
    "query",
    "description",
    "subagent_type",
    "skill",
    "notebook_path",
    "prompt",
)

MAX_ARG_CHARS = 160

registry = ("claude",)


def summarise_args(tool_name: str, args: dict) -> str:
    """Render a tool call's arguments as one short, safe line."""
    if not isinstance(args, dict):
        return ""
    parts = []
    for key in SAFE_ARG_KEYS:
        value = args.get(key)
        if not isinstance(value, str) or not value.strip():
            continue
        value = " ".join(value.split())
        if len(value) > MAX_ARG_CHARS:
            value = value[:MAX_ARG_CHARS] + "…"
        parts.append(value if key in ("command", "description", "prompt") else f"{key}={value}")
        if len(parts) == 2:
            break
    return " ".join(parts)


def load(name: str):
    """Import a host adapter by name, or return None if it isn't available."""
    if name not in registry:
        return None
    try:
        return importlib.import_module(f"hosts.{name}")
    except ImportError:
        return None


def detect():
    """Return the first adapter that recognises the current environment."""
    for name in registry:
        module = load(name)
        if module is not None and module.detect():
            return module
    return None
