#!/usr/bin/env python3
"""Reduce a session transcript to a small, ranked digest of *behavioural* signal.

A transcript is mostly tool output and prose that says nothing about how the
user wants to work. This throws that away and keeps the handful of moments that
do: where they corrected the agent, where they stopped it, where it got things
wrong on its own.

Two modes:

    --score     print one integer, the total signal weight. The session-end
                hook reads this to decide whether analysing the session is
                worth spending money on.
    (default)   print the digest itself, ready to hand to a model.

Nothing here calls a model, and nothing leaves the machine.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import sys
from collections import Counter
from pathlib import Path

_LIB = Path(__file__).resolve().parent
sys.path[:0] = [str(_LIB), str(_LIB / "hosts")]

import base as host_base  # noqa: E402

# How much each kind of moment is worth. A correction the user typed is worth
# an order of magnitude more than a tool that happened to fail.
WEIGHT_FEEDBACK = 10
WEIGHT_DENIAL = 5
WEIGHT_CORRECTIVE = 3
WEIGHT_TOOL_ERROR = 1
WEIGHT_CHURN = 2

CORRECTIVE = re.compile(
    r"(?:^|\W)(?:no[,.]|nope|don'?t\b|do not\b|instead\b|actually\b|i told you|"
    r"why did you|why are you|stop\b|that'?s (?:not|wrong)|not what i|"
    r"revert\b|undo\b|never\b|should(?:n'?t| not)\b|rather than)",
    re.IGNORECASE,
)

# The host also writes into the feedback field when the user picks a canned
# action rather than typing. Those sentences describe the harness, not a
# preference, and reading them as corrections produces rules about nothing.
SYNTHETIC_FEEDBACK = re.compile(
    r"^\s*(?:the user (?:wants to clarify|doesn't want to proceed|rejected)|"
    r"\[Request interrupted|no response requested)",
    re.IGNORECASE,
)

# Anything shaped like a credential is removed before the digest is written.
SECRETS = [
    (re.compile(r"\b(?:sk|pk)-[A-Za-z0-9_\-]{16,}"), "«key»"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{16,}"), "«token»"),
    (re.compile(r"\bAKIA[0-9A-Z]{12,}"), "«aws-key»"),
    (re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}"), "«token»"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "«private-key»"),
    (re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}\b"), "«blob»"),
    (re.compile(r"(?i)\b(?:authorization|api[_-]?key|password|secret|token)\s*[:=]\s*\S+"),
     "«redacted»"),
]

EDIT_TOOLS = {"Edit", "Write", "NotebookEdit", "MultiEdit", "str_replace_editor", "apply_patch"}

# Text the host injects into the user role that the user never typed. Reading it
# as if they had produces rules built on the harness talking to itself.
SYNTHETIC = re.compile(
    r"^\s*(?:<task-notification>|<system-reminder>|<local-command-|<command-name>|"
    r"<command-message>|<bash-input>|<bash-stdout>|\[Request interrupted|"
    r"Caveat: The messages below|API Error|\[Tool )",
    re.IGNORECASE,
)


def scrub(text: str) -> str:
    for pattern, replacement in SECRETS:
        text = pattern.sub(replacement, text)
    return text


def redacted_path(text: str, globs) -> bool:
    return any(fnmatch.fnmatch(text, pattern) or fnmatch.fnmatch(Path(text).name, pattern)
               for pattern in globs)


def clip(text: str, limit: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[:limit] + "…"


class Digest:
    """Everything worth keeping from one session, plus what it's worth."""

    def __init__(self, redact_globs, project_root=None):
        self.redact = list(redact_globs or [])
        self.root = Path(project_root).resolve() if project_root else None
        self.corrections = []      # (ts, feedback, what the agent was about to do)
        self.refusals = []         # (ts, what the agent was about to do)
        self.corrective_turns = []
        self.failures = []
        self.asks = []
        self.tool_counts = Counter()
        self.file_touches = Counter()
        self.user_turns = 0
        self.tool_calls = 0

    def feed(self, events):
        pending = ""  # what the assistant most recently proposed doing
        for event in events:
            if event["role"] == "assistant":
                for call in event["tools"]:
                    self.tool_calls += 1
                    self.tool_counts[call["name"]] += 1
                    if call["name"] in EDIT_TOOLS:
                        match = re.search(r"(?:file_path|path)=(\S+)", call["summary"])
                        if match and self._is_project_file(match.group(1)):
                            self.file_touches[match.group(1)] += 1
                    label = call["name"]
                    if call["summary"]:
                        label += f' — {call["summary"]}'
                    pending = clip(label, 150)
                continue

            text = scrub(event["text"])
            if SYNTHETIC.match(text):
                text = ""
            feedback = scrub(event["feedback"] or "")
            if SYNTHETIC_FEEDBACK.match(feedback):
                feedback = ""

            if feedback:
                self.corrections.append((event["ts"], clip(feedback, 400), pending))
            elif event["denial"]:
                self.refusals.append((event["ts"], pending))

            if text:
                self.user_turns += 1
                self.asks.append((event["ts"], clip(text, 300)))
                if CORRECTIVE.search(text) and not feedback:
                    self.corrective_turns.append((event["ts"], clip(text, 300)))

            # A refusal already arrives as an error; counting it again would
            # read the user's judgement as the agent's own mistake.
            if event["tool_error"] and pending and not (feedback or event["denial"]):
                self.failures.append((event["ts"], pending))

    def _is_project_file(self, path: str) -> bool:
        if redacted_path(path, self.redact):
            return False
        if self.root is None:
            return True
        try:
            return Path(path).resolve().is_relative_to(self.root)
        except (OSError, ValueError):
            return False

    @property
    def churn(self):
        return [(path, n) for path, n in self.file_touches.most_common() if n > 2]

    @property
    def score(self) -> int:
        return (
            WEIGHT_FEEDBACK * len(self.corrections)
            + WEIGHT_DENIAL * len(self.refusals)
            + WEIGHT_CORRECTIVE * len(self.corrective_turns)
            + WEIGHT_TOOL_ERROR * min(len(self.failures), 10)
            + WEIGHT_CHURN * len(self.churn)
        )

    def render(self, session_id: str, max_chars: int) -> str:
        out = [
            "# Session digest",
            "",
            f"session: {session_id or 'unknown'}  ·  {self.user_turns} user turns  ·  "
            f"{self.tool_calls} tool calls  ·  signal score {self.score}",
            "",
            "Ranked strongest signal first. Everything below is evidence of how the user",
            "wants work done. Tool output and file contents are deliberately absent.",
        ]

        def section(title, rows, note=""):
            if not rows:
                return
            out.extend(["", f"## {title}"])
            if note:
                out.append(f"_{note}_")
            out.append("")
            out.extend(rows)

        section(
            "Corrections the user typed (strongest signal)",
            [
                line
                for ts, feedback, pending in self.corrections[:8]
                for line in (
                    f'- [{ts[:19]}] "{feedback}"',
                    *([f"  - it was about to: {pending}"] if pending else []),
                )
            ],
            "They stopped the agent and explained why. Treat each as a standing rule.",
        )

        section(
            "Actions the user refused without explaining",
            [f"- [{ts[:19]}] it was about to: {pending or 'unknown'}"
             for ts, pending in self.refusals[:8]],
            "No reason given — infer what the user objected to from the action itself.",
        )

        section(
            "Corrective language mid-conversation",
            [f'- [{ts[:19]}] "{text}"' for ts, text in self.corrective_turns[:8]],
        )

        section(
            "Things that failed on the agent's own initiative",
            [f"- {pending}" for _, pending in self.failures[:6]],
            "Mistakes nobody had to point out. Worth a rule only if the cause is general.",
        )

        section(
            "Files rewritten repeatedly",
            [f"- {path} — touched {n}x" for path, n in self.churn[:6]],
            "Repeated rewrites usually mean the first approach was wrong.",
        )

        if self.asks:
            rows = [f'- first: "{self.asks[0][1]}"']
            if len(self.asks) > 1:
                rows.append(f'- last:  "{self.asks[-1][1]}"')
            section("What the session was about", rows)

        if self.tool_counts:
            summary = ", ".join(f"{name} ×{n}" for name, n in self.tool_counts.most_common(8))
            section("Tool usage shape", [f"- {summary}"])

        text = "\n".join(out) + "\n"
        if len(text) > max_chars:
            text = text[:max_chars].rsplit("\n", 1)[0] + "\n\n_(digest truncated)_\n"
        return text


def build(transcript: Path, redact_globs, project_root=None) -> Digest:
    adapter = host_base.load(os.environ.get("PATTERN_HOST", "claude"))
    if adapter is None:
        raise SystemExit("pattern: no host adapter available for this environment")
    digest = Digest(redact_globs, project_root)
    digest.feed(adapter.iter_events(transcript))
    return digest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript", help="path to the session transcript")
    parser.add_argument("--session-id", default="")
    parser.add_argument("--score", action="store_true", help="print the signal score only")
    parser.add_argument("--max-chars", type=int, default=6000)
    parser.add_argument("--redact", default="", help="comma-separated globs to exclude")
    parser.add_argument("--cwd", default="", help="project root; file churn outside it is ignored")
    parser.add_argument("--out", default="", help="write the digest here instead of stdout")
    args = parser.parse_args()

    path = Path(args.transcript).expanduser()
    if not path.is_file():
        if args.score:
            print(0)
            return 0
        raise SystemExit(f"pattern: no such transcript: {path}")

    globs = [g.strip() for g in args.redact.split(",") if g.strip()]
    digest = build(path, globs, args.cwd or None)

    if args.score:
        print(digest.score)
        return 0

    rendered = digest.render(args.session_id, args.max_chars)
    if args.out:
        Path(args.out).write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
