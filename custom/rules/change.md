# How a change moves — team conventions

Goes at the top of AGENTS.md §B, adapted to the repo. The ledgers it names are in
`ledgers.md`.

1. **Branch.** Off `main`, one branch and one worktree per writer. Rendered output (a
   PDF, an image, a built page) goes to the one folder the repo's AGENTS.md names for it
   in the person's main checkout, never only into a worktree, so there is one place to
   look. A long-running process (a loop, a server) runs from its own checkout.
2. **One milestone.** One logical change, a test that fails without it, `make check`, one
   commit. Small and buildable, not a day-long branch.
3. **Show it.** Run the change for real once. Until then it is listed in
   `.agent/DEFERRED_VERIFICATION.md`.
4. **Route what is not the task.** Anything noticed on the way goes to a ledger, not into
   this change.
5. **Integrate.** Up to date with `main`, `make check`, one independent review pass, then
   at most one recheck; what it finds after that is fixed forward. Open a pull request;
   the person merges it on GitHub. Push only when the person says so; never force-push.
6. **Close.** Once merged: remove the worktree, delete the branch, and in the main
   checkout `git switch main && git pull --ff-only`, which tags the release when the repo
   uses the `auto-release` hook. Ledgers updated, nothing left open.

## Where each fact lives

One place per fact; no second copy anywhere. A repository creates only the files it needs.

| Fact | Owner |
|---|---|
| Rules, commands, gates, how a change moves | `AGENTS.md` |
| What the thing is for and for whom | `docs/PRODUCT.md`, only if the README does not say it |
| Why it is built the way it is | `docs/ARCHITECTURE.md` |
| Work a person has chosen to do | `docs/BACKLOG.md` |
| Setup, first run, everyday use | `README.md` |
| What changed for users | `CHANGELOG.md` |
| Open observations and proposals | the ledgers in `.agent/` |

Code and tests own the behaviour. Documents keep intent and decisions, not a second
implementation. Every document states how things are, not how they came to be.
