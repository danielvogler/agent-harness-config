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
- A clone or worktree goes beside the main checkout, never in `/tmp` or a scratchpad.
  Credentials can be chosen by the folder git runs in, so a push from elsewhere fails.
- One working session per repository unless the person starts another. Open work goes
  into the repo, not only into chat.

## Batches, reviews and asks

- A job over several items is done in one go: take the usual default for each open
  question, note it, and list every decision once at the end.
- With several background agents, reply once when all are back; at most one progress
  line while waiting.
- After the person answers a review's questions and says to go ahead, the whole review
  is the work order. List only what was left out, and why.
- An ask for the person's action names the place (the link, the screen, the button) and
  what happens if it is not done.

## Edits and drafts

- A style edit (corners, line width, spacing) applies to every sibling on that frame,
  page or deck, not only the element named.
- When hand-made drafts of a logo or illustration are rejected twice, stop drafting.
  Offer a designer brief or a proper drawing tool.

## Never trace a shell that may hold a token

No `set -x` or `bash -x` around anything that may call gh, git or a cloud CLI: a shell
function wrapping it can read a token, and the trace prints it. Debug with `echo` lines.

## Deliverables stay local

An HTML page, dashboard or report is written to the repo or the scratchpad and opened
with `open`. Never publish it to a hosted service (claude.ai artifacts, a gist, a paste
site) unless the person asks for that service by name.
