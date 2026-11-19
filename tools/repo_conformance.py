#!/usr/bin/env python3
"""repo-conformance: check a repo's `.agent/` ledgers and agent entry files.

custom/rules/ledgers.md says a ledger lists only what is open, an empty ledger is
not created, and row ids carry the ledger's prefix. Nothing enforced that, so
settled rows piled up and AGENT_IMPROVEMENTS rows sat for months. This reads the
tables in `.agent/*.md`, plus AGENTS.md and CLAUDE.md, and prints one line per
problem as `file:line: level: message`.

Errors (exit 1): an existing ledger with no rows, a settled status, an id without
the ledger's prefix. Warnings (exit 0): an AGENT_IMPROVEMENTS row older than
MAX_IMPROVEMENT_AGE_DAYS, a missing AGENTS.md, a CLAUDE.md that is more than a
short pointer to AGENTS.md.

Published as a pre-commit hook in .pre-commit-hooks.yaml; this repo runs the same
file as a local hook.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path
from typing import NamedTuple

# Ledger file -> id prefix. None: the ledger is keyed by commit, not by id.
LEDGERS: dict[str, str | None] = {
    "FINDINGS.md": "F",
    "DEFERRED_VERIFICATION.md": None,
    "AGENT_IMPROVEMENTS.md": "A",
    "UPSTREAM_ISSUES.md": "U",
}
SETTLED = re.compile(r"\b(done|declined|dropped|verified|closed|merged)\b", re.I)
DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
SEPARATOR_CELL = re.compile(r"^:?-+:?$")
CELL_DECORATION = "`*_~ "
MAX_IMPROVEMENT_AGE_DAYS = 14
MAX_POINTER_LINES = 5
ERROR, WARNING = "error", "warning"


class Problem(NamedTuple):
    path: str
    line: int
    level: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.level}: {self.message}"


class Row(NamedTuple):
    line: int
    cells: dict[str, str]
    first: str


def split_cells(line: str) -> list[str]:
    """The cells of a markdown table line; `\\|` inside a cell is not a separator."""
    body = line.strip().removeprefix("|").removesuffix("|")
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", body)]


def is_separator(cells: list[str]) -> bool:
    return bool(cells) and all(SEPARATOR_CELL.match(cell.replace(" ", "")) for cell in cells)


def table_rows(text: str) -> list[Row]:
    """Data rows of every table in the text, keyed by lower-cased header name."""
    rows: list[Row] = []
    header: list[str] | None = None
    previous: list[str] | None = None
    in_table = False
    for number, raw in enumerate(text.splitlines(), start=1):
        if not raw.lstrip().startswith("|"):
            header, previous, in_table = None, None, False
            continue
        cells = split_cells(raw)
        if is_separator(cells):
            header = [cell.strip(CELL_DECORATION).lower() for cell in previous or []]
            in_table = previous is not None
            continue
        if in_table and header is not None:
            keyed = dict(zip(header, cells, strict=False))
            rows.append(Row(number, keyed, cells[0] if cells else ""))
        previous = cells
    return rows


def column(row: Row, *names: str) -> str:
    """The first cell whose header contains one of the names, else ''."""
    for header, value in row.cells.items():
        if any(name in header for name in names):
            return value
    return ""


def row_age_days(row: Row, today: dt.date) -> int | None:
    """Days since the earliest date in the row's evidence or date column, if any."""
    dates = []
    for match in DATE.finditer(column(row, "evidence", "date")):
        try:
            dates.append(dt.date.fromisoformat(match.group(1)))
        except ValueError:
            continue
    return (today - min(dates)).days if dates else None


def check_row(name: str, path: str, row: Row, today: dt.date) -> list[Problem]:
    problems = []
    prefix = LEDGERS[name]
    status = column(row, "status")
    settled = SETTLED.search(status)
    if settled:
        problems.append(
            Problem(
                path,
                row.line,
                ERROR,
                f"status '{settled.group(1)}': a settled row is deleted in the commit "
                "that settles it",
            )
        )
    row_id = row.first.strip(CELL_DECORATION)
    if prefix and not re.fullmatch(rf"{prefix}\d+", row_id):
        problems.append(
            Problem(path, row.line, ERROR, f"id '{row_id}' does not have the form {prefix}<n>")
        )
    age = row_age_days(row, today) if name == "AGENT_IMPROVEMENTS.md" else None
    if age is not None and age > MAX_IMPROVEMENT_AGE_DAYS:
        problems.append(
            Problem(
                path,
                row.line,
                WARNING,
                f"{row_id} is {age} days old: accept it, decline it, or propose it to "
                "the harness repo",
            )
        )
    return problems


def check_ledger(root: Path, name: str, today: dt.date) -> list[Problem]:
    file = root / ".agent" / name
    if not file.is_file():
        return []
    path = file.relative_to(root).as_posix()
    rows = table_rows(file.read_text(encoding="utf-8"))
    if not rows:
        return [Problem(path, 1, ERROR, "ledger has no rows: an empty ledger is not created")]
    return [problem for row in rows for problem in check_row(name, path, row, today)]


def check_entry_files(root: Path) -> list[Problem]:
    problems = []
    if not (root / "AGENTS.md").is_file():
        problems.append(Problem("AGENTS.md", 1, WARNING, "missing: AGENTS.md holds the rules"))
    claude = root / "CLAUDE.md"
    if claude.is_file():
        text = claude.read_text(encoding="utf-8")
        lines = [line for line in text.splitlines() if line.strip()]
        if len(lines) > MAX_POINTER_LINES:
            problems.append(
                Problem(
                    "CLAUDE.md",
                    MAX_POINTER_LINES + 1,
                    WARNING,
                    f"{len(lines)} lines: CLAUDE.md is a short pointer to AGENTS.md",
                )
            )
        if "AGENTS.md" not in text:
            problems.append(Problem("CLAUDE.md", 1, WARNING, "does not point to AGENTS.md"))
    return problems


def check(root: Path, today: dt.date) -> list[Problem]:
    ledgers = [problem for name in LEDGERS for problem in check_ledger(root, name, today)]
    return ledgers + check_entry_files(root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repo root (default: .)")
    # pre-commit may pass file names; the check always covers the whole repo.
    parser.add_argument("files", nargs="*", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    problems = check(args.root.resolve(), dt.date.today())
    for problem in problems:
        print(problem)
    return 1 if any(problem.level == ERROR for problem in problems) else 0


if __name__ == "__main__":
    sys.exit(main())
