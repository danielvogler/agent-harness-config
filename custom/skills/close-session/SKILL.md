---
name: close-session
description: Use when the person asks whether a session can be closed ("can I close this?", "anything left?", "are we done?"). Checks the repo, branches, pull requests, worktrees and ledgers, and answers with what is still open.
---

# Can this session be closed?

Answer from evidence, not from memory of the conversation. Run the checks, then reply.

## Checks

Run each in every repo this session touched, including worktrees and copies.

1. **Uncommitted work.** `git status --short`. Name each file, and say whether it is
   this session's work or was there before.
2. **Unpushed commits.** `git log --oneline @{u}..` on every branch this session
   created or committed to. No upstream at all counts as unpushed.
3. **Pull requests.** `gh pr list --author @me --state open` for this repo, and
   `gh pr view` for any this session opened: open, merged, or failing checks.
4. **Worktrees and branches.** `git worktree list`. A worktree whose branch is merged
   can go; give the exact `git worktree remove` and `git branch -d` commands.
5. **Running work.** Background shells, subagents, loops or scheduled wake-ups this
   session started. Closing the session stops them.
6. **Ledgers.** Rows this session added to `.agent/*.md` that are now settled, and
   commits that still belong in `.agent/DEFERRED_VERIFICATION.md`.
7. **Only-here knowledge.** Decisions or facts that live only in this conversation.
   Write them to their owner (a ledger, AGENTS.md, memory) or offer a handoff.

## Reply

Lead with the verdict in one sentence: "Yes, you can close it" or "Not yet: two things
are open". Then list only what is open, each with the exact command or the decision it
needs. Nothing open means no list.
