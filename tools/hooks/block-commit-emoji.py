#!/usr/bin/env python3
"""PreToolUse guard: refuse a `git commit` whose message carries an emoji.

custom/rules/git.md bans emoji in commit messages in every repo, gitmoji repos
included. A repo's own commit-msg hook only exists where the repo adopted it, so
this guard covers the commits an agent makes anywhere. It reads the Bash command
Claude Code is about to run and blocks (exit 2) when an emoji follows `git ...
commit` in it, which covers -m, --amend and a heredoc passed to -F -.

Unreadable input is let through: a guard that fails closed on a parsing error
would block every Bash call.
"""

from __future__ import annotations

import json
import re
import sys

# `commit` must be git's subcommand: only `-c key=value` or `-C dir` may sit between.
GIT_COMMIT = re.compile(r"(?:^|[\s;&|(])git(?:\s+-[cC]\s+\S+)*\s+commit\b")
HEREDOC = re.compile(r"<<-?\s*['\"]?(\w+)")
SEPARATORS = (";", "|", "&", "\n")
# Emoji, not every symbol: arrows, check marks and prompt glyphs (\u2192 \u2713 \u276f)
# stay allowed. .pre-commit-config.yaml spells the same set as UTF-8 bytes for
# pygrep; a test keeps the two in step.
EMOJI = re.compile(
    "[\U0001f000-\U0001faff\u2600-\u26ff"
    "\u2702\u2705\u2708\u2709\u270f\u2712\u2728"
    "\u274c\u274e\u2753-\u2755\u2757\u2764\u2795-\u2797\u27b0\u27bf"
    "\u2b05-\u2b07\u2b1b\u2b1c\u2b50\u2b55\u23e9-\u23ff\u231a\u231b"
    "\u2139\u203c\u2049]"
)
BLOCKED = 2


def unquoted_end(text: str) -> int:
    """Index of the first `;`, `|`, `&` or newline outside quotes, else len(text)."""
    quote = ""
    index = 0
    while index < len(text):
        char = text[index]
        if char == "\\" and quote != "'":
            index += 2  # the escaped character never opens, closes or separates
            continue
        if quote:
            quote = "" if char == quote else quote
        elif char in "'\"":
            quote = char
        elif char in SEPARATORS:
            return index
        index += 1
    return len(text)


def commit_message_part(command: str, start: int) -> str:
    """The commit command's own text: up to the next unquoted separator, or its heredoc."""
    rest = command[start:]
    head = rest[: unquoted_end(rest)]
    heredoc = HEREDOC.search(head)
    if heredoc is None:
        return head
    closing = re.search(rf"^\s*{heredoc.group(1)}\s*$", rest[heredoc.end() :], re.M)
    return rest[: heredoc.end() + closing.start()] if closing else rest


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        command = payload["tool_input"]["command"]
    except (ValueError, KeyError, TypeError):
        return 0
    commit = GIT_COMMIT.search(command)
    if commit is None or EMOJI.search(commit_message_part(command, commit.end())) is None:
        return 0
    print(
        "Blocked: the commit message has an emoji. Commit messages carry no emoji "
        "in any repo (custom/rules/git.md). Remove it and commit again.",
        file=sys.stderr,
    )
    return BLOCKED


if __name__ == "__main__":
    sys.exit(main())
