---
description: Research AI agent frameworks and coding assistants
---

ROLE: You are a Lead AI Architect and Market Researcher conducting a comprehensive, neutral, and structured review of the current landscape of AI agent harnesses, deep agent frameworks, and top coding assistants (CLI and IDE-integrated).

METHODOLOGY: Load the `custom-deep-research` skill before starting. It defines the three-phase pipeline (Discovery, Extraction, Report Generation), folder layout, save-with-fallback chain, source-count gate, anti-hallucination guardrails, and the final self-review. Follow that pipeline strictly. Everything below is the topic-specific overlay.

TOPIC SLUG: `agent-frameworks` (artifacts under `research/agent-frameworks/`)

SOURCE-COUNT TARGET: 25+

PHASE 1 — Search angles (fan out 6+ websearch calls in parallel):
- Multi-agent orchestration frameworks (LangGraph, CrewAI, AutoGen, Semantic Kernel)
- CLI-based coding assistants (Claude Code, Codex CLI, Aider, Goose)
- IDE-integrated coding assistants (Cursor, Copilot, Windsurf, Continue)
- Agent harnesses for tool use, planning, memory management
- Open-source vs proprietary agent frameworks — adoption metrics
- Benchmarks and evaluations (SWE-bench, HumanEval, AgentBench)
- Academic papers on agent architectures (actor models, state machines, ReAct, reflection)

Source diversity — saved sources should span at least 3 of:
- Academic papers / technical reports
- Industry benchmarks / evaluations
- Framework documentation / architecture overviews
- Comparative analyses / market reports
- Community adoption data (GitHub stars, contributors, ecosystem stats)

Abstract-level data (key stats, architecture patterns, findings) is acceptable when full text is unavailable.

PHASE 2 — Per-source extraction, capture:
- Title, author or organization, year, source type
- Framework or assistant name and category
- Architecture patterns: memory model, planning strategy, tool-use mechanism
- Key capabilities and limitations
- Benchmark results with exact numbers
- Pricing model (if applicable)
- Developer experience notes (adoption, ecosystem, integrations)

Group findings into:
(a) Agent orchestration frameworks
(b) Coding assistants — CLI
(c) Coding assistants — IDE
(d) Benchmarks and evaluation methodologies
(e) Architecture patterns

PHASE 3 — Reports (4 markdown reports, ~2,000–3,000 words each) in `generated_reports/`:

1. `01_market_landscape.md`
   - Overview of the agent framework and coding assistant ecosystem
   - Key players by category with adoption metrics
   - Open-source vs proprietary market split

2. `02_architectural_deep_dive.md`
   - Memory, planning, tool use, orchestration in state-of-the-art frameworks
   - Comparison of architecture patterns (ReAct, reflection, actor model, DAG)
   - Context management, multi-step reasoning, agent-to-agent communication

3. `03_capability_matrix.md`
   - Structured comparison table across all tools
   - Dimensions: terminal integration, multi-file editing, agent-to-agent comms, tool creation, memory persistence, planning, cost, open-source status
   - Strengths, limitations, recommended use cases

4. `04_future_trends.md`
   - Autonomous agents vs copilot models — trajectory analysis
   - Emerging patterns (MCP, A2A protocol, agentic RAG)
   - Ecosystem predictions and investment trends

---

## Discipline beyond the skill

Four rules the `custom-deep-research` skill does not cover. They are not topic-specific —
keep them identical across the deep-research commands so they can be promoted into a
skill of our own if a third command ever needs them.

1. **Log every search, not just failed downloads.** `failed.log` records fetches that
   broke; nothing records what was searched. Keep `sources/search-log.md`, one row per
   search, written the moment the search returns and never reconstructed at the end:

   | # | Angle | Query, verbatim | Outcome |

   Outcome is the file the search produced, or the reason it produced none. Searches that
   found nothing are the point of the log — a log holding only successes cannot be checked
   by anyone, including you.

2. **Search for the opposite, once per angle.** Before closing an angle: state its main
   claim in one sentence, write the strongest opposing version a serious person could
   hold, and run at least one search built to find evidence for that version — using
   different words from the ones that found the original. The same words return the same
   pages and confirm what you already have. Log the outcome either way, including when
   the counter-search finds nothing.

3. **Never check a claim by asking the model again.** A model repeats its mistakes
   identically across runs, so two passes agreeing proves nothing. Checking means opening
   the file under `sources/` and finding the sentence.

4. **Check for the same source saved twice.** Before Phase 3, compare saved sources by
   normalised title and by URL, not only by filename — the same paper arrives from arXiv,
   a publisher and a lab page under three different slugs, and the filename dedupe does
   not catch it. Fold the second copy into the first, note anything it added, and record
   the dropped filename in `_index.md`.
