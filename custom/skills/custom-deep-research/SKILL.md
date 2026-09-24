---
name: custom-deep-research
description: Methodology for multi-phase, citation-grounded research pipelines. Load when a task involves mapping a market, surveying a technology landscape, or producing a structured report grounded in primary sources rather than general knowledge.
allowed-tools: Bash, Read, Write, Glob, Grep, WebSearch, WebFetch, Task
---

# Deep Research

A disciplined pipeline for producing comprehensive, cited, hallucination-resistant research reports. This skill encodes the shared methodology so topic-specific research commands do not have to restate it individually.

## When to load

Load this skill when the task fits any of these shapes:

- "Research X for me", "do a deep dive on Y", "give me a comprehensive overview of Z"
- Mapping a competitive landscape, market, regulatory environment, or technology ecosystem
- Surveying academic literature plus industry sources on a domain
- Producing a structured markdown report that must be defensible against fact-checking

Do not load this skill for: quick factual lookups, single-page summaries, code debugging, or any task where one or two sources would suffice.

## Core principles

1. **Avoid hallucination of effort.** Every claim in the final report traces back to a source file you actually downloaded and read with the Read tool. General LLM knowledge is not evidence.
2. **Strict phase ordering.** Phase 1 must clear its source-count gate before Phase 2 begins. Phase 2 must read every source before Phase 3 writes anything substantive.
3. **Parallelize within a phase, never across phases.** Inside Phase 1, fan out searches and downloads aggressively. Do not start reading sources while still searching.
4. **One folder per topic.** All artifacts live under `research/<topic>/`. Do not pollute the rest of the repo.
5. **Idempotent restarts.** Treat the `sources/` folder as ground truth. Re-running mid-pipeline should resume, not re-download.

## Project layout

For topic slug `<topic>` (kebab-case, derived from the request), create on first invocation:

```
research/<topic>/
  sources/                # raw downloaded content (PDFs, HTML-to-markdown)
  agent_scripts/          # any automation scripts written during the run
  generated_reports/      # final markdown deliverables
```

Also create `research/.gitignore` containing a single line, `*`, on first invocation
if it does not already exist. A run downloads tens of megabytes of third-party PDFs
into whatever repository you happen to be standing in, and none of it belongs in
version control. Ignoring the output from inside the output directory means this
holds in every repo the command is ever run in, without each of them needing to
know the skill exists.

Supporting files that emerge during the run:

- `sources/failed.log` — URLs that failed every fetch attempt, one per line, with HTTP status or error
- `sources/_index.md` — running manifest mapping each saved file to its origin URL and a one-line summary
- `extraction-notes.md` — working notes from Phase 2 (not a deliverable; never publish this)

## Phase 1: Discovery and data hunting

Goal: populate `sources/` with enough diverse, primary documents to support a defensible report.

### Source-count target

The invoking command specifies the target. Calibrate the command's target to the breadth of the topic — narrow domains need fewer sources, broad multi-segment surveys need many more. The number is a floor, not a ceiling. If unspecified, ask before starting.

### Search strategy

1. Before searching, brainstorm distinct topic angles in writing — different sub-questions, different stakeholders, different source types. Do not skip this step; it is what prevents shallow research.
2. Fire websearch calls in parallel, one per angle, several concurrent in the first round.
3. Cap each angle at three rounds of searching. If an angle has not produced new sources after three rounds, move on; do not loop indefinitely.

### Source diversity rule

Before declaring Phase 1 complete, verify the saved sources span at least three of these categories:

- Academic papers and technical reports
- Industry benchmarks, analyst reports, or evaluations
- Vendor, framework, or company official documentation
- News and journalism from well-sourced outlets
- Government, regulator, or statistical-office publications
- Community discourse (well-cited blog posts, conference talks, forum threads)

If fewer than three categories are represented, run targeted searches for the missing ones before moving on.

### Save-with-fallback chain

For each candidate URL, try to save the content using this strict order. Move to the next step only on failure:

1. **Direct file download** for PDFs and other static files:
   ```bash
   curl --max-time 30 -L -o research/<topic>/sources/<slug>.<ext> "<url>"
   ```
2. **HTML to markdown via the webfetch tool**, then `write` the returned markdown to `research/<topic>/sources/<slug>.md`. Prefer this over curl for publisher websites — they frequently block bots, while webfetch is more reliable.
3. **Log and skip.** Append the URL and the reason for failure to `research/<topic>/sources/failed.log`. Continue.

Rules:

- No more than one retry per URL across the entire chain.
- Filenames: slugify to lowercase, alphanumeric plus dashes only. Dedupe collisions with `-2`, `-3` suffixes.
- Skip paywalled and login-gated pages. Log them.
- Before each new save, check whether the target slug already exists in `sources/`. If it does, do not re-fetch — Phase 1 is idempotent and a re-run should resume from where it left off.

### Hard gate before Phase 2

Count the saved sources (excluding bookkeeping files like `failed.log` and `_index.md`). If the count is below the command's target, return to brainstorming new angles. Do not advance to Phase 2 unless either the target is met, or three full rounds have been exhausted on every angle — in which case proceed and document the coverage gap explicitly in the executive summary.

## Phase 2: Extraction

Goal: structured findings grounded in the files actually saved, not in search-result snippets.

### Mandatory full read pass

Use the Read tool on every file in `sources/`. No skipping based on filename. No summarizing from a search snippet. Do not delegate this pass to a librarian or summary agent — the agent that writes the report must be the one that read every source. If a source is unreadable (corrupt PDF, encoding error, garbled OCR), note it in `failed.log` and continue with the rest.

### What to extract per source

For each file, capture:

- **Exact statistics** with units, time periods, and methodology when stated. Always pair a number with its source, its measurement window, and any scope qualifier.
- **Named entities** — companies, products, regulators, frameworks — each with a one-line role description.
- **Direct quotes worth citing**, with file path and page number for PDFs.
- **Contradictions and counter-evidence** across sources. Flag explicitly when two sources disagree on a number or claim.

Maintain `research/<topic>/extraction-notes.md` (or topic-bucketed files if the corpus is large). This is working memory.

### Anti-hallucination guardrails

- Every entity, statistic, or claim in your notes must trace to a `sources/<file>` path you read in this run.
- If you cannot cite, mark the claim with the literal token `[uncertain]` and either re-open Phase 1 to search for supporting evidence or drop the claim from the final report. The published report must contain zero `[uncertain]` markers.
- Never fill gaps with general LLM knowledge. If the corpus does not support a claim, the claim does not belong in the report.

## Phase 3: Report generation

Goal: publication-quality markdown reports in `generated_reports/`.

### Required deliverables

Calibrate the set to the topic, but at minimum produce:

- `00-executive-summary.md` — one page, headline findings, key numbers, coverage gaps
- `01-<core-topic>.md` through `0N-<sub-topic>.md` — deep sections per angle from Phase 1
- `99-sources.md` — annotated source list (file path, origin URL, one-line description, category from the diversity list)

### Quality bar

- Every numeric claim cited inline with a relative link to the source file (path under `../sources/`).
- Tables for comparable data: prices, vendors, feature matrices, regional comparisons. Use markdown tables, not prose lists.
- Neutral tone. No marketing language. No superlatives unless they come from a cited source.
- Coverage-gap section in the executive summary if Phase 1 fell short of target. Name what is missing and why.

### Final self-review gate

Before declaring the run complete:

1. Search the generated reports for the tokens `[uncertain]`, `TBD`, `TODO`, `FIXME` — they must not appear anywhere in published files.
2. Spot-check at least five random citations: open the cited file, search for the claim, confirm it is actually present with the cited figure.
3. Diff the executive summary's headline numbers against the same numbers in the detailed sections. They must match exactly.

## Common anti-patterns

These appear repeatedly when the pipeline is rushed. If you catch yourself doing any of them, stop and return to the matching phase.

- Synthesizing an overview from general knowledge while Phase 1 is still running
- Writing reports from search-result snippets without saving and reading the underlying pages
- Reading a handful of sources thoroughly and skimming the rest
- Retrying a failed URL multiple times instead of logging and moving on
- Skipping the source-count gate because "I have enough material" (you do not)
- Quoting vendor marketing copy as if it were neutral evidence
- Letting `[uncertain]` markers reach the published report
- Re-downloading sources that already exist in `sources/` instead of resuming
- Delegating the Phase 2 read pass to a librarian or summary agent

## Relationship to topic-specific commands

Topic commands supply only the topic-specific overlay: role framing, the topic slug, the source-count target for this run, the angles to brainstorm during Phase 1, and the expected report set. Everything in this skill is the shared methodology those commands rely on.

When writing a new topic command, load this skill by its full name — `custom-deep-research` —
and do not restate the pipeline above. Provide:

- The role framing for the analyst persona
- The topic slug to use under `research/`
- The source-count target for this specific topic
- The angles to brainstorm during Phase 1
- The expected report sections and any topic-specific extraction fields

Reference this skill for the rest.
