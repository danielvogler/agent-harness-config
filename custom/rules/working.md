# Working with the person

Extends ECC's `common/` rules with what people on this team corrected agents for most.

## Options or one answer

- **A matter of taste** (colour, wording, naming, layout): offer two to four lettered
  options with concrete values (hex codes, the exact wording) and change nothing until
  one is picked. "Make a suggestion" asks for options, not for an edit.
- **A how-to question**: give the one path you recommend and its steps. Add at most one
  alternative, and only when it changes the outcome. A survey of every way confuses.

## A decision stays decided

When the person decides something, write it to where it lasts in the same turn: the
ledger row, the commit message, the brief or memory. Never ask it again, also not after
the conversation was summarized. Read the summary's list of decisions before asking.

## Say where the work happens

- Before moving or renaming a repository or project folder, say so and wait. A shell or
  session open inside it breaks with `getcwd` errors.
- A session that works in a worktree or a copy names that path in its first reply, and
  says when the work moves back.

## Deliverables stay local

An HTML page, dashboard or report is written to the repo or the scratchpad and opened
with `open`. Never publish it to a hosted service (claude.ai artifacts, a gist, a paste
site) unless the person asks for that service by name.
