# Git — team additions

Add a scope: `fix(storage): ...`, not `fix: ...`. The scope is the area touched.

No emoji in a commit message, in any repo, gitmoji repos included. The type and scope
already say what an emoji would. A Claude Code hook and the repo's commit-msg hook refuse it.

## Shape of a message

Subject in the imperative, under 72 characters, no trailing full stop. Then a blank line,
then bullets — not paragraphs. Wrap at 72.

```
fix(qr): compute the payment amount from the line items

- The QR payload read a stored total that could disagree with the bill.
- Totals are now derived at render time; the stored field is gone.
- Adds a regression test for the CHF 10 mismatch this caused.
```

Say **why** in the message; the diff already shows what. One logical change per commit — if
the bullets need an "also", it is two commits.

## A commit is read by a stranger in two years

**Nothing that needs the session to make sense.** No "as discussed", "as you asked", "per
the review", "the issue you mentioned", "fixed the thing from earlier". No `I`, no `we`, no
apologies, no narration of the process. State the change, not the conversation that
produced it.

Never name an agent, model, tool or session, and **never add AI attribution** — no
`Co-Authored-By` trailer for a tool and no "Generated with ..." line, in a commit message or
in a PR description. Commits and PRs are authored by the person whose name is on them.

`make setup-user` turns Claude Code's attribution off, and a `commit-msg` hook plus a PR
check reject it; do not work around either. A repo that wants it back sets `attribution`
in its own `.claude/settings.json` and leaves out the hook and the check.

## Never commit an absolute path

Not in the message, not in code, not in a committed `.agent/` or `.claude/` file. Write
`backend/scripts/import.js`, never `/Users/<someone>/...`: that breaks for everyone else and
for CI, and in a commit message it survives forever. If one is unavoidable in code, ask
first and leave a comment above it saying why.

## Staging and history

- **Stage named paths.** `git add -A` and `git add .` are how `.DS_Store`, a stray notebook
  and a 200 MB output file get committed. Run `git status` first and look.
- **Never `--no-verify`.** The hook is the convention; skipping it removes the convention.
- **Say the working tree is about to change** before a rebase, reset, checkout or stash,
  and wait. Prefer a squash that leaves the tree untouched.
- **Never rewrite history that is already pushed** to a shared branch.
- Commit or push only when asked. If on the default branch, branch first.
- **Regroup before the pull request:** one commit per logical change, before the push.

## Pushing

The person's setup decides which credential pushes where. Before the first push, run
`git push --dry-run`; if it is refused, give the person the exact push command and open the
pull request once they have pushed. Never switch remote URL, protocol, token or SSH key.

## Filing an issue via API or MCP

`.github/ISSUE_TEMPLATE/` is a web-UI convenience the REST API, and any MCP tool built on
it, never sees. Read the matching template first and copy its title, label and headings.
