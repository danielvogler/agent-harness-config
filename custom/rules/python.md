---
paths:
  - "**/*.py"
  - "**/*.pyi"
  - "**/pyproject.toml"
  - "**/*.ipynb"
---
# Python — team conventions

## Tooling (overrides upstream)

- **`uv`** for environments, dependencies and locking — not pip, poetry or conda.
  `uv sync` is the setup step; commit `uv.lock`.
- **`ruff check` and `ruff format`** — not black, not isort, not flake8. Line length 110,
  Google docstring convention. Upstream names black + isort; ignore that here.
- **`mypy` strict** and **`pytest`**, both on pre-push rather than pre-commit.
- Hooks via **`prek`**; tasks via a **`justfile`** or **`Makefile`** whose `check` is fmt →
  lint → typecheck → test and runs exactly what CI runs.
- CI is **GitLab** on self-hosted infrastructure, **GitHub Actions** on the public repos.
  Check the remote before writing a pipeline.

## Layout

`src/<package>/` with `tests/` alongside — not a flat module dump at the repo root. One
module per concern; split at ~400 lines rather than growing a 2000-line `utils.py`.

Notebooks are for exploration and figures, never a deliverable and never imported. The
moment a cell is worth running twice it moves into `src/` and the notebook imports it — a
pipeline that only exists as a notebook is not reproducible.

## Signatures

- **No `**kwargs` as a catch-all.** It swallows typos silently, kills autocompletion and
  makes type checking impossible. Declare every parameter with a name and a type. The
  exception is a genuine pass-through wrapper — a decorator, `__init_subclass__`.
- **No `_` prefix on module-level helpers**, and `__name` only inside a class — at module
  level the interpreter does no mangling, so both signal "internal" and enforce nothing.

## Non-negotiables

- **Type hints on every public signature.** Internal helpers can go without.
- **`logging`, never `print`** outside CLI entry points; configure it once at the entry.
- **`pathlib.Path`, not `os.path`** — never string concatenation for paths.
- **No bare `except:`**, no `except Exception: pass`. A swallowed traceback costs hours.
- **No secrets or absolute personal paths in source.** Read from the environment.
- **Seed every stochastic process explicitly** and log the seed.

## Scientific code

- **Vectorising changes the answer.** Float summation order differs, so replacing a loop
  with numpy is not a refactor: compare against the loop with `np.allclose` at a stated
  tolerance before deleting it. Vectorise once it works — correct and slow beats fast and
  wrong.
- **Check shapes and units at function boundaries, and `raise` — never `assert`.** Asserts
  vanish under `python -O`, so the guard is absent in the run that matters. Put the unit in
  the name (`depth_m`, `rate_m3_s`): a name is read every time, a comment never. Unit
  errors are our most expensive bug class, and they are silent.
- **Never `==` on floats**, and decide at the boundary what NaN means. `np.mean` propagates
  it, `np.nanmean` hides it; choosing by accident is how a wrong number reaches a figure.
