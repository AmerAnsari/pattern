#!/usr/bin/env bash
# Set the version in every manifest listed in .version-bump.json, in lockstep.
# Usage: scripts/bump-version.sh 0.2.0
set -euo pipefail

VERSION="${1:-}"
if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+([-.][A-Za-z0-9.]+)?$ ]]; then
  echo "usage: $0 <semver>   e.g. $0 0.2.0" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 - "$VERSION" <<'PY'
import json, sys, pathlib

version = sys.argv[1]
spec = json.loads(pathlib.Path(".version-bump.json").read_text())

for entry in spec["files"]:
    path = pathlib.Path(entry["path"])
    data = json.loads(path.read_text())
    node = data
    parts = entry["field"].split(".")
    for part in parts[:-1]:
        node = node[int(part)] if part.isdigit() else node[part]
    node[parts[-1]] = version
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"  {path}  ->  {version}")
PY

echo "bumped to $VERSION"

STALE=$(grep -rln --exclude-dir=.git --exclude=.version-bump.json --exclude=CHANGELOG.md \
  -E '"version": *"[0-9]+\.[0-9]+\.[0-9]+"' . | while read -r f; do
    grep -q "\"version\": *\"$VERSION\"" "$f" || echo "$f"
  done)
if [ -n "$STALE" ]; then
  echo "WARNING: files with a version that was not bumped:" >&2
  echo "$STALE" >&2
  exit 1
fi
