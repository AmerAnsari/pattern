#!/usr/bin/env bash
# Create this project's data directory, if it isn't there already.
# Idempotent: existing files are never touched.
#
# Usage: bootstrap.sh [project-root]
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# The project root comes from the caller, or from where the shell is.
ROOT="${1:-$(python3 "$HERE/config.py" path root)}"

DATA="$(cd "$ROOT" && python3 "$HERE/config.py" path data)"
mkdir -p "$DATA"

if [ ! -f "$DATA/config.json" ]; then
  cat > "$DATA/config.json" <<'JSON'
{
  "_comment": "Overrides for patternscribe. Anything you leave out keeps its default; run `/patternscribe config` to see the merged result.",
  "auto_capture": true,
  "use_superpowers": true
}
JSON
fi

if [ ! -f "$DATA/PATTERNS.md" ]; then
  FINGERPRINT="$(git -C "$ROOT" remote get-url origin 2>/dev/null || echo "$ROOT")"
  cat > "$DATA/PATTERNS.md" <<MD
# Learned patterns

project: $FINGERPRINT
updated: $(date +%Y-%m-%d)
sessions analyzed: 0

<!--
Maintained by patternscribe, which updates this file when you run /patternscribe.
Hand-written bullets are kept. Mark a bullet \`(pinned)\` to protect it from being
reworded, recounted or archived. \`(seen Nx)\` is how often a pattern has recurred:
1x is a hypothesis, 5x is a rule.
-->

## Working agreement — how to collaborate here

_Nothing learned yet._

## Engineering defaults — what this user would choose

_Nothing learned yet._

## Do / Don't — hard rules from corrections

### Do

_Nothing learned yet._

### Don't

_Nothing learned yet._

## Archive — not reinforced recently
MD
fi

if [ ! -f "$DATA/journal.md" ]; then
  cat > "$DATA/journal.md" <<'MD'
# Evidence journal

Why each rule in PATTERNS.md exists: what was said, when, and in which session.
Append-only. `/patternscribe why <rule>` searches this file.
MD
fi

echo "$DATA"
