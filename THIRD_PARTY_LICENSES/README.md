# Third-party licenses

Skills in `custom/skills/` copied from other repositories keep their original license. Each
source's license text is in this directory, fetched from its default branch on 2026-09-24.
Everything else in this repository is Apache-2.0 (see `LICENSE`).

| Source | License | Text | Skills |
| --- | --- | --- | --- |
| [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) | MIT | [addyosmani-agent-skills.txt](addyosmani-agent-skills.txt) | `api-and-interface-design`, `browser-testing-with-devtools`, `ci-cd-and-automation`, `code-review-and-quality`, `code-simplification`, `context-engineering`, `debugging-and-error-recovery`, `deprecation-and-migration`, `documentation-and-adrs`, `doubt-driven-development`, `git-workflow-and-versioning`, `idea-refine`, `incremental-implementation`, `interview-me`, `performance-optimization`, `planning-and-task-breakdown`, `security-and-hardening`, `shipping-and-launch`, `source-driven-development`, `spec-driven-development`, `test-driven-development`, `using-agent-skills` |
| [antonbabenko/terraform-skill](https://github.com/antonbabenko/terraform-skill) | Apache-2.0 | [antonbabenko-terraform-skill.txt](antonbabenko-terraform-skill.txt) | `terraform-skill` |
| [callstackincubator/agent-skills](https://github.com/callstackincubator/agent-skills) | MIT | [callstackincubator-agent-skills.txt](callstackincubator-agent-skills.txt) | `github`, `validate-skills` |
| [dbt-labs/dbt-agent-skills](https://github.com/dbt-labs/dbt-agent-skills) | Apache-2.0 | [dbt-labs-dbt-agent-skills.txt](dbt-labs-dbt-agent-skills.txt) | `auditing-skills` |
| [forrestchang/andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills) | MIT | [forrestchang-andrej-karpathy-skills.txt](forrestchang-andrej-karpathy-skills.txt) | `karpathy-guidelines` |
| [google-gemini/gemini-skills](https://github.com/google-gemini/gemini-skills) | Apache-2.0 | [google-gemini-gemini-skills.txt](google-gemini-gemini-skills.txt) | `gemini-api-dev`, `gemini-interactions-api`, `gemini-live-api-dev` |
| [google/adk-python](https://github.com/google/adk-python) | Apache-2.0 | [google-adk-python.txt](google-adk-python.txt) | `adk-agent-builder`, `adk-architecture`, `adk-debug`, `adk-sample-creator`, `adk-setup`, `adk-style` |
| [hashicorp/agent-skills](https://github.com/hashicorp/agent-skills) | MPL-2.0 | [hashicorp-agent-skills.txt](hashicorp-agent-skills.txt) | `terraform-style-guide`, `terraform-test` |
| [K-Dense-AI/claude-scientific-writer](https://github.com/K-Dense-AI/claude-scientific-writer) | MIT | [K-Dense-AI-claude-scientific-writer.txt](K-Dense-AI-claude-scientific-writer.txt) | `citation-management`, `literature-review`, `peer-review`, `research-grants`, `scholar-evaluation`, `scientific-critical-thinking`, `scientific-writing` |
| [langchain-ai/langchain-skills](https://github.com/langchain-ai/langchain-skills) | MIT | [langchain-ai-langchain-skills.txt](langchain-ai-langchain-skills.txt) | `deep-agents-core`, `deep-agents-memory`, `deep-agents-orchestration` |
| [openai/codex](https://github.com/openai/codex) | Apache-2.0 | [openai-codex.txt](openai-codex.txt) and [NOTICE](openai-codex.NOTICE.txt) | `babysit-pr`, `code-review` |

## Files changed from their source

Apache-2.0 §4(b) asks that changed files say so. These are the only ones:

- `custom/skills/adk-agent-builder/references/advanced-patterns.md` (google/adk-python) — an
  absolute link to the original author's local copy of `dynamic-nodes.md` replaced with a
  relative link to the same file.

## Adding a source

Put its license text here as `<owner>-<repo>.txt`, plus its `NOTICE` if it has one, and add
a row above. `make validate` fails if a source in `custom/skills/skills-lock.json` has no
license file here.
