---
paths:
  - "**/agents/**"
  - "**/agent/**"
  - "**/prompts/**"
  - "**/*prompt*.py"
  - "**/*agent*.py"
---
# Building agents — team conventions

> ECC's `common/agents.md` covers orchestrating the agents *you* run; this is about agents
> *we ship*. Both install under `~/.claude/rules/ecc/`.
>
> The engineering detail lives in installed skills — `agent-harness-construction`,
> `autonomous-loops`, `cost-aware-llm-pipeline`, `agent-architecture-audit`, and the
> `adk-*` set. Load one rather than growing this file. What stays here is only what those
> skills do not say, because we are a research group and they are not.

## Prompts are code

They live in their own files, version-controlled and reviewed — not in triple-quoted
strings scattered through the source. A prompt change is a behaviour change.

## Every autonomous loop needs a ceiling

Max iterations, max spend, or a wall clock — set before the first run, not after the
surprise. Anything irreversible (writes to shared storage, deletes, sends, publishes)
needs a human in the loop, or a dry-run mode that is the default.

## Evaluation

- **A behaviour without a test is a rumour.** Before an agent is relied on, write the
  handful of cases that define "working", including the failure cases.
- Evaluate on held-out examples the prompt was not tuned against.
- **Record the model and its version with every result.** Model updates change behaviour,
  and undated agent output is not citable.

## Scientific integrity

This is the part with no equivalent anywhere else in this config.

- An agent may draft, search and summarise. **It does not get to be the source of a
  factual claim.** Every number and citation traces to a document a human can open.
- Log every tool call — name, arguments, outcome. Persist the full trace of any run whose
  output reaches a paper or a decision. An agent you cannot replay is one whose results
  you cannot defend.
- Never let generated text into a manuscript without recording what was generated and who
  checked it. Journals and funders increasingly require the disclosure.
