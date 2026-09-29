#!/usr/bin/env python3
"""Guard the version number that lives in five manifests at once.

Two rules:

1. **The manifests agree.** Every file listed in `.version-bump.json` carries the
   same version. A half-bump makes the marketplace advertise one version while
   installing another, and nothing at install time complains.

2. **Only a release PR may change it.** Ordinary PRs leave the version alone, so
   a month of merges doesn't fight over the same five lines. A PR that does move
   it must be titled `Release <version>`, and that version must match the files.

Run it locally before pushing:

    python3 scripts/check-versions.py

Run it in CI, where the base branch and the PR title are both known:

    python3 scripts/check-versions.py --base-ref origin/main --pr-title "$TITLE"

Standard library only, like the rest of this repo.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

RELEASE_TITLE = re.compile(r"^Release\s+v?(\d+\.\d+\.\d+(?:[-.][A-Za-z0-9.]+)?)\s*$")
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)")

ROOT = Path(__file__).resolve().parent.parent


def dig(data, field: str):
    """Walk a dotted path, treating digits as list indices ('plugins.0.version')."""
    for part in field.split("."):
        data = data[int(part)] if part.isdigit() else data[part]
    return data


def spec() -> list[dict]:
    return json.loads((ROOT / ".version-bump.json").read_text(encoding="utf-8"))["files"]


def versions_here() -> dict[str, str]:
    return {
        entry["path"]: dig(json.loads((ROOT / entry["path"]).read_text(encoding="utf-8")),
                           entry["field"])
        for entry in spec()
    }


def version_at(ref: str) -> str | None:
    """The version on another ref, read through git so no checkout is needed."""
    entry = spec()[0]
    try:
        blob = subprocess.run(
            ["git", "show", f"{ref}:{entry['path']}"],
            capture_output=True, text=True, check=True, cwd=ROOT,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    try:
        return dig(json.loads(blob), entry["field"])
    except (ValueError, KeyError, IndexError):
        return None


def newer(candidate: str, existing: str) -> bool:
    def parts(value):
        found = SEMVER.match(value)
        return tuple(int(g) for g in found.groups()) if found else (0, 0, 0)
    return parts(candidate) > parts(existing)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-ref", default="",
                        help="branch this PR targets, e.g. origin/main; enables rule 2")
    parser.add_argument("--pr-title", default="", help="the pull request title")
    args = parser.parse_args()

    found = versions_here()
    problems: list[str] = []

    # Rule 1 — the manifests agree.
    distinct = set(found.values())
    if len(distinct) > 1:
        problems.append("The manifests disagree about the version:")
        for path, version in found.items():
            problems.append(f"    {version:10} {path}")
        problems.append("")
        problems.append("  Run:  ./scripts/bump-version.sh <version>")
        problems.append("  It writes all of them at once, which is the point of it.")

    current = next(iter(distinct)) if len(distinct) == 1 else None

    # Rule 2 — only a release PR may change it.
    if args.base_ref and current:
        base = version_at(args.base_ref)
        title = args.pr_title.strip()
        claimed = RELEASE_TITLE.match(title)

        if base is None:
            print(f"note: could not read the version on {args.base_ref}; skipping rule 2")
        elif current != base:
            if not claimed:
                problems.append(
                    f"This PR changes the version ({base} -> {current}), but its title is not a "
                    "release.")
                problems.append("")
                problems.append("  Ordinary PRs leave the version alone — it moves once per")
                problems.append("  release, so a month of merges doesn't fight over the same")
                problems.append("  five lines.")
                problems.append("")
                problems.append("  Either revert the version change, or retitle the PR:")
                problems.append(f"      Release {current}")
            elif claimed.group(1) != current:
                problems.append(
                    f'Title says "Release {claimed.group(1)}" but the manifests say {current}.')
                problems.append("  Make them match before merging.")
            elif not newer(current, base):
                problems.append(f"Version goes backwards: {base} -> {current}.")
                problems.append("  Releases only ever move forward; users cannot downgrade.")
        elif claimed:
            problems.append(
                f'Title claims "Release {claimed.group(1)}" but the version is unchanged '
                f"({current}).")
            problems.append("")
            problems.append("  Run:  ./scripts/bump-version.sh <version>")

    if problems:
        print("✘ version check failed\n", file=sys.stderr)
        for line in problems:
            print(f"  {line}", file=sys.stderr)
        print(file=sys.stderr)
        return 1

    print(f"✔ all {len(found)} manifests agree on {current}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
