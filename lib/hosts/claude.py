"""Claude Code host adapter.

Transcripts are JSON Lines at ~/.claude/projects/<slugified-cwd>/<session-id>.jsonl.
Each line is one record; the ones worth reading are `type: "user"` and
`type: "assistant"`. Everything else (hook attachments, mode changes, titles,
file-history snapshots) is bookkeeping and is dropped.

Two fields carry far more signal than anything else in the file:

    toolDenialKind  the user refused an action the agent was about to take
    userFeedback    the sentence they typed to explain why

They appear together on a `type: "user"` record. That pair is a correction
recorded as structured data, which is the whole reason this adapter exists.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import base

NAME = "claude"
DISPLAY_NAME = "Claude Code"


def detect() -> bool:
    return bool(os.environ.get("CLAUDE_PROJECT_DIR")) or projects_root().is_dir()


def projects_root() -> Path:
    config = os.environ.get("CLAUDE_CONFIG_DIR")
    base_dir = Path(config) if config else Path.home() / ".claude"
    return base_dir / "projects"


def slugify(cwd: str | Path) -> str:
    """Mirror how Claude Code names a project's transcript directory."""
    return re.sub(r"[^A-Za-z0-9]", "-", str(Path(cwd).resolve()))


def transcript_dir(cwd: str | Path) -> Path:
    return projects_root() / slugify(cwd)


def find_transcript(session_id: str, cwd: str | Path, hint: str | None = None) -> Path | None:
    """Locate a session's transcript. `hint` is the path the hook handed us."""
    if hint:
        candidate = Path(hint).expanduser()
        if candidate.is_file():
            return candidate
    if session_id:
        candidate = transcript_dir(cwd) / f"{session_id}.jsonl"
        if candidate.is_file():
            return candidate
    return None


def recent_transcripts(cwd: str | Path, since_mtime: float = 0.0) -> list[Path]:
    """Transcripts touched since `since_mtime`, oldest first."""
    directory = transcript_dir(cwd)
    if not directory.is_dir():
        return []
    found = [p for p in directory.glob("*.jsonl") if p.stat().st_mtime > since_mtime]
    return sorted(found, key=lambda p: p.stat().st_mtime)


def _text_of(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    chunks = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            chunks.append(str(block.get("text", "")))
    return "\n".join(chunks).strip()


def _tools_of(content) -> list[dict]:
    if not isinstance(content, list):
        return []
    calls = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "tool_use":
            name = str(block.get("name", "?"))
            summary = base.summarise_args(name, block.get("input"))
            calls.append({"name": name, "summary": summary})
    return calls


def _errored(content) -> bool:
    if not isinstance(content, list):
        return False
    return any(
        isinstance(block, dict) and block.get("type") == "tool_result" and block.get("is_error")
        for block in content
    )


def iter_events(path: str | Path):
    """Yield normalised events. Malformed lines are skipped, not fatal —
    a transcript can be truncated if the session died mid-write."""
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except (ValueError, TypeError):
                continue
            if not isinstance(record, dict):
                continue
            if record.get("type") not in ("user", "assistant"):
                continue
            if record.get("isMeta"):
                continue

            message = record.get("message") or {}
            content = message.get("content")

            yield {
                "ts": record.get("timestamp", ""),
                "role": record.get("type"),
                "text": _text_of(content),
                "feedback": (record.get("userFeedback") or None),
                "denial": (record.get("toolDenialKind") or None),
                "tools": _tools_of(content),
                "tool_error": _errored(content),
                "sidechain": bool(record.get("isSidechain")),
            }
