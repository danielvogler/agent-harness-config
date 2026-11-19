"""tools/repo_conformance.py: the `.agent/` ledger and entry-file check."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

TODAY = dt.date(2026, 3, 31)
FINDINGS_HEADER = "| # | Finding | Status | Proposed | Evidence |\n|---|---|---|---|---|\n"
IMPROVEMENTS_HEADER = "| # | Proposal | Evidence | Status |\n|---|---|---|---|\n"


def make_repo(root: Path, ledgers: dict[str, str], claude: str | None = "See AGENTS.md.\n"):
    (root / "AGENTS.md").write_text("# Rules\n")
    if claude is not None:
        (root / "CLAUDE.md").write_text(claude)
    for name, text in ledgers.items():
        path = root / ".agent" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {name}\n\nIntro.\n\n{text}")
    return root


def messages(problems, level=None):
    return [str(p) for p in problems if level is None or p.level == level]


def test_a_conforming_repo_has_no_problems(conformance, tmp_path):
    # Arrange
    make_repo(
        tmp_path,
        {
            "FINDINGS.md": FINDINGS_HEADER + "| F1 | Cache is stale | open | now | `abc123` |\n",
            "DEFERRED_VERIFICATION.md": "| Commit | Change | Risk | Evidence |\n"
            "|---|---|---|---|\n| `abc123` | new target | untested | a real run |\n",
            "AGENT_IMPROVEMENTS.md": IMPROVEMENTS_HEADER
            + "| A1 | Lint docs | 2026-03-25: two typos | proposed |\n",
            "UPSTREAM_ISSUES.md": "| # | Upstream | Behaviour | Workaround | Report |\n"
            "|---|---|---|---|---|\n| U1 | tool | breaks | pin | none |\n",
        },
    )

    # Act
    problems = conformance.check(tmp_path, TODAY)

    # Assert
    assert problems == []


@pytest.mark.parametrize("body", ["", FINDINGS_HEADER, "Nothing open.\n"])
def test_an_existing_ledger_without_rows_is_an_error(conformance, tmp_path, body):
    # Arrange
    make_repo(tmp_path, {"FINDINGS.md": body})

    # Act
    problems = conformance.check(tmp_path, TODAY)

    # Assert
    assert messages(problems) == [
        ".agent/FINDINGS.md:1: error: ledger has no rows: an empty ledger is not created"
    ]


@pytest.mark.parametrize(
    "status", ["done", "Declined", "dropped", "verified 2026-03-01", "**closed**", "merged"]
)
def test_a_settled_status_is_an_error_with_its_line(conformance, tmp_path, status):
    # Arrange
    make_repo(tmp_path, {"FINDINGS.md": FINDINGS_HEADER + f"| F1 | x | {status} | now | y |\n"})

    # Act
    problems = conformance.check(tmp_path, TODAY)

    # Assert
    (problem,) = problems
    assert (problem.path, problem.line, problem.level) == (".agent/FINDINGS.md", 7, "error")
    assert "settled row is deleted" in problem.message


def test_a_settled_word_outside_the_status_column_is_fine(conformance, tmp_path):
    # Arrange
    row = "| F1 | the job is done twice | open | drop | merged in `abc` |\n"
    make_repo(tmp_path, {"FINDINGS.md": FINDINGS_HEADER + row})

    # Act
    problems = conformance.check(tmp_path, TODAY)

    # Assert
    assert problems == []


@pytest.mark.parametrize(
    ("ledger", "header", "bad_id"),
    [
        ("FINDINGS.md", FINDINGS_HEADER, "1"),
        ("FINDINGS.md", FINDINGS_HEADER, "A3"),
        ("AGENT_IMPROVEMENTS.md", IMPROVEMENTS_HEADER, "F2"),
        ("UPSTREAM_ISSUES.md", "| # | Upstream | Behaviour |\n|---|---|---|\n", "C1"),
    ],
)
def test_an_id_without_the_ledger_prefix_is_an_error(conformance, tmp_path, ledger, header, bad_id):
    # Arrange
    cells = " | ".join([bad_id] + ["x"] * (header.count("|", 0, header.index("\n")) - 2))
    make_repo(tmp_path, {ledger: header + f"| {cells} |\n"})

    # Act
    problems = conformance.check(tmp_path, TODAY)

    # Assert
    assert [p.level for p in problems] == ["error"]
    assert f"id '{bad_id}'" in problems[0].message


def test_decorated_ids_and_loose_tables_are_accepted(conformance, tmp_path):
    # Arrange: bold and backticked ids, aligned separators, an escaped pipe in a cell
    # and a row without its closing pipe.
    text = (
        "| # | Finding | Status |\n| :-- | :-: | --: |\n"
        "| **F1** | a \\| b | open |\n| `F2` | c | open\n"
    )
    make_repo(tmp_path, {"FINDINGS.md": text})

    # Act
    problems = conformance.check(tmp_path, TODAY)

    # Assert
    assert problems == []


def test_deferred_verification_rows_need_no_id(conformance, tmp_path):
    # Arrange
    make_repo(
        tmp_path,
        {
            "DEFERRED_VERIFICATION.md": "| Commit | Change | Risk | Evidence |\n"
            "|---|---|---|---|\n| `feat/x` | y | z | a run |\n"
        },
    )

    # Act
    problems = conformance.check(tmp_path, TODAY)

    # Assert
    assert problems == []


def test_an_old_improvement_is_a_warning_only(conformance, tmp_path, monkeypatch, capsys):
    # Arrange
    rows = (
        "| A1 | old | 2026-03-01: seen, again 2026-03-30 | proposed |\n"
        "| A2 | recent | 2026-03-20: seen | proposed |\n"
        "| A3 | undated | two sessions clashed | proposed |\n"
    )
    make_repo(tmp_path, {"AGENT_IMPROVEMENTS.md": IMPROVEMENTS_HEADER + rows})

    class FixedDate(dt.date):
        @classmethod
        def today(cls):
            return TODAY

    monkeypatch.setattr(conformance.dt, "date", FixedDate)

    # Act
    code = conformance.main(["--root", str(tmp_path)])

    # Assert
    out = capsys.readouterr().out.splitlines()
    assert code == 0
    assert out == [
        ".agent/AGENT_IMPROVEMENTS.md:7: warning: A1 is 30 days old: accept it, decline it, "
        "or propose it to the harness repo"
    ]


def test_errors_set_a_non_zero_exit(conformance, tmp_path, capsys):
    # Arrange
    make_repo(tmp_path, {"UPSTREAM_ISSUES.md": "No table here.\n"})

    # Act
    code = conformance.main(["--root", str(tmp_path), "ignored-file-name.py"])

    # Assert
    assert code == 1
    assert ".agent/UPSTREAM_ISSUES.md:1: error:" in capsys.readouterr().out


def test_missing_agents_md_is_a_warning(conformance, tmp_path):
    # Act
    problems = conformance.check(tmp_path, TODAY)

    # Assert
    assert messages(problems) == ["AGENTS.md:1: warning: missing: AGENTS.md holds the rules"]


def test_a_long_claude_md_is_a_warning(conformance, tmp_path):
    # Arrange
    make_repo(tmp_path, {}, claude="See AGENTS.md.\n" + "Rule.\n" * 6)

    # Act
    problems = conformance.check(tmp_path, TODAY)

    # Assert
    assert messages(problems, "warning") == [
        "CLAUDE.md:6: warning: 7 lines: CLAUDE.md is a short pointer to AGENTS.md"
    ]
    assert messages(problems, "error") == []


def test_a_claude_md_that_does_not_point_to_agents_md_is_a_warning(conformance, tmp_path):
    # Arrange
    make_repo(tmp_path, {}, claude="Be nice.\n")

    # Act
    problems = conformance.check(tmp_path, TODAY)

    # Assert
    assert messages(problems) == ["CLAUDE.md:1: warning: does not point to AGENTS.md"]


def test_this_repo_conforms(conformance):
    # Act
    problems = conformance.check(Path(__file__).resolve().parent.parent, dt.date.today())

    # Assert
    assert problems == []
