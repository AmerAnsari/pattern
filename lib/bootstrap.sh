#!/usr/bin/env bash
# Create this project's pattern data directory, if it isn't there already.
# Idempotent: existing files are never touched.
#
# Usage: bootstrap.sh [project-root]
set -euo pipefail

LIB="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${1:-${PATTERNSCRIBE_CWD:-$PWD}}"

DATA="$(PATTERNSCRIBE_CWD="$ROOT" python3 "$LIB/config.py" path data)"
STATE="$DATA/state"

mkdir -p "$STATE"

# Transient files are the plugin's business, not the repo's.
if [ ! -f "$STATE/.gitignore" ]; then
  printf '*\n' > "$STATE/.gitignore"
fi

if [ ! -f "$DATA/config.json" ]; then
  cat > "$DATA/config.json" <<'JSON'
{
  "_comment": "Overrides for the pattern plugin. Anything you leave out keeps its default; run `/patternscribe config` to see the merged result.",
  "enabled": true,
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
Maintained by the \`pattern\` plugin, which rewrites this file after a session ends.
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
