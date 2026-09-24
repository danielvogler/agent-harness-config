#!/usr/bin/env bash
# Print one tag's section of CHANGELOG.md, and fail if it has none.
#
# The release workflow uses the same answer twice: it refuses a tag whose
# changelog has no entry, then uses that entry as the GitHub release notes. One
# script for both means the notes checked and the notes published cannot drift.
#
# Usage: scripts/changelog-section.sh v0.2.0 [path/to/CHANGELOG.md]
set -euo pipefail

tag="${1:-}"
changelog="${2:-CHANGELOG.md}"

if [ -z "$tag" ]; then
  echo "usage: scripts/changelog-section.sh <tag> [changelog]" >&2
  exit 2
fi

if [ ! -f "$changelog" ]; then
  echo "no such file: $changelog" >&2
  exit 2
fi

# Headings here are `## [v0.1.0] — 2026-07-30`. The section ends at the next
# `## ` heading, or at the `[v0.1.0]: https://...` link definitions at the foot
# of the file, so the oldest release's notes do not end in a list of URLs.
section=$(
  awk -v heading="## [$tag]" '
    index($0, heading) == 1 { found = 1; next }
    found && /^## / { exit }
    found && /^\[[^]]+\]: / { exit }
    found { print }
  ' "$changelog"
)

# Trim the blank lines the heading and the next one leave behind.
section=$(printf '%s\n' "$section" | sed -e '/./,$!d' | sed -e :a -e '/^\n*$/{$d;N;};/\n$/ba')

if [ -z "$section" ]; then
  echo "$changelog has no '## [$tag]' section, or it is empty" >&2
  exit 1
fi

printf '%s\n' "$section"
