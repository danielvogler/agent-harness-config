"""tools/hooks/block-commit-emoji.py: the PreToolUse guard against emoji in commits."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parent.parent / "tools" / "hooks" / "block-commit-emoji.py"


def run_hook(command: str) -> subprocess.CompletedProcess:
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    "command",
    [
        'git commit -m "docs(site): \U0001f4dd add the docs site"',
        "git commit -q -F - <<'EOF'\nfix(core): \U0001f41b widen the cap\nEOF",
        'cd repo && git add a.py && git commit -m "ci(github): \U0001f477 one forge"',
        'git commit --amend -m "feat: ✨ report every design"',
        'git -C repo commit -m "fix: \U0001f1e8\U0001f1ed swiss flag"',
        'git commit -m "docs: \u2b05 back"',
        'git commit -m "chore: \u23f3 wait"',
        'git commit -m "fix(ui): closes #12 \U0001f389"',
        'git commit -m "fix: a; b \U0001f41b"',
        'git commit -m "fix: subject\n\n- body line \U0001f4dd"',
        "git commit -m 'fix: single \U0001f4dd'",
        'git commit -m "fix: say \\"hi\\"; then \U0001f4dd"',
        "git commit -m \"$(cat <<'EOF'\nfix: subject\n\n- body \U0001f4dd\nEOF\n)\"",
    ],
)
def test_blocks_a_commit_whose_message_has_an_emoji(command):
    # Act
    result = run_hook(command)

    # Assert
    assert result.returncode == 2
    assert "emoji" in result.stderr


@pytest.mark.parametrize(
    "command",
    [
        'git commit -m "docs(site): add the docs site"',
        'echo "✅ done" && git status',
        'git log --format="%s" | grep "\U0001f4dd"',
        "ls -la",
        'git commit -m ok && echo "\U0001f389 done"',
        "git commit -m ok; echo \u2713",
        'git log --grep=commit "\U0001f600"',
        'git commit -m "fix: \u2713 checks \u2192 next \u276f prompt"',
    ],
)
def test_lets_everything_else_through(command):
    # Act
    result = run_hook(command)

    # Assert
    assert result.returncode == 0


def test_lets_unreadable_input_through():
    # Act
    result = subprocess.run(
        [sys.executable, str(HOOK)], input="not json", capture_output=True, text=True, check=False
    )

    # Assert
    assert result.returncode == 0


def test_commit_msg_hook_and_guard_flag_the_same_characters():
    # The pygrep hook spells the ranges as UTF-8 bytes, the guard as code points;
    # this keeps the two copies from drifting apart.
    import importlib.util
    import re

    config = (HOOK.parent.parent.parent / ".pre-commit-config.yaml").read_text()
    entry = re.search(r"id: no-emoji-in-commit.*?entry: '([^']+)'", config, re.S).group(1)
    pygrep = re.compile(entry.encode())
    spec = importlib.util.spec_from_file_location("guard", HOOK)
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)

    for code in [*range(0x2000, 0x2C00), *range(0x1F000, 0x1FB00)]:
        char = chr(code)
        assert bool(pygrep.search(char.encode())) == bool(guard.EMOJI.search(char)), hex(code)
