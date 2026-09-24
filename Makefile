PROFILE ?= custom
ECC     := .ecc

# ECC installs one target per invocation, and only these three are user-scoped
# ("home" targets). cursor and antigravity are project-scoped in ECC — see
# `make install-project` and the note in README.md.
TARGETS ?= claude codex opencode

.DEFAULT_GOAL := help
.PHONY: help setup opencode-payload install install-project reinstall plan doctor context check test conventions setup-user mcp bump uninstall update validate audit clean

help: ## Show this help
	@grep -hE '^[a-zA-Z-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-9s\033[0m %s\n", $$1, $$2}'

# install-hooks builds every hook environment up front, so a broken one fails setup here
# instead of blocking the first commit. The run after it may still report findings in
# existing files, which is why only that step is allowed to fail.
setup: ## Set up this repo for contributing (git hooks) — not needed just to install
	@command -v pre-commit >/dev/null 2>&1 || { \
		echo "pre-commit not found. Install it with: uv tool install pre-commit"; exit 1; }
	pre-commit install
	pre-commit install-hooks
	pre-commit run --all-files || true
	@echo
	@echo "Hooks active. They run on every commit to this repo."

# opencode needs a compiled plugin payload under .ecc/.opencode/dist before its target
# will install, and building it needs upstream's own dev dependencies — the TypeScript
# compiler in particular. A fresh .ecc/ has no node_modules, so `make reinstall` used to
# uninstall everything and then die here, leaving the harness directories empty. Install
# them first; npm is idempotent and a no-op once they are there.
opencode-payload:
	@case " $(TARGETS) " in *" opencode "*) \
		test -d $(ECC)/node_modules || { \
			echo "==> installing upstream dev dependencies (first build only)"; \
			( cd $(ECC) && npm install --silent --no-audit --no-fund ) || exit 1; }; \
		echo "==> building opencode payload"; \
		( cd $(ECC) && node scripts/build-opencode.js ) ;; \
	esac

# ECC's installer overwrites ~/.codex/AGENTS.md and ~/.opencode/AGENTS.md, which are the
# files setup-user appends the team conventions to — and for Codex that append is the ONLY
# route those conventions arrive by, since Codex has no rules layer. So an install silently
# undid setup-user. --restore puts it back, and does nothing at all if setup-user has never
# been run here (it keys off a stamp file, so a first install still turns nothing on).
#
# --enable-hooks is required from upstream 2.2.1 onward: the installer refuses to write the
# hook runtime without an explicit yes. It copies the hook scripts AND, unlike 2.1.0, wires
# its whole registry into ~/.claude/settings.json — upstream's fix for "hooks are installed
# but not wired" in UPSTREAM.md. On the 2026-09-12 bump that took us from 2 wired matchers
# to 27 without anyone asking for it.
#
# We keep --enable-hooks so the scripts land (--no-hooks would remove block-no-verify and
# config-protection with them), and `setup-user.py` then resets the "hooks" key to just
# those two. Read setup_hooks() before changing either half; they are one decision.
install: ## Install into every user-scoped harness (run once per person)
	python3 tools/materialize.py
	@$(MAKE) -s opencode-payload
	@for t in $(TARGETS); do \
		echo "==> $$t"; $(ECC)/install.sh --profile $(PROFILE) --enable-hooks --target $$t || exit 1; \
	done
	@python3 tools/setup-user.py --restore


install-project: ## Install cursor/antigravity into one project: make install-project PROJECT=/path
	@test -n "$(PROJECT)" || { echo "usage: make install-project PROJECT=/path/to/repo"; exit 1; }
	python3 tools/materialize.py
	@abs="$$(cd $(ECC) && pwd)"; for t in cursor antigravity; do \
		echo "==> $$t into $(PROJECT)"; \
		( cd "$(PROJECT)" && "$$abs/install.sh" --profile $(PROFILE) --target $$t ) || exit 1; \
	done

plan: ## Show what install would write, without writing anything
	python3 tools/materialize.py
	@$(MAKE) -s opencode-payload
	@for t in $(TARGETS); do \
		echo "==> $$t"; $(ECC)/install.sh --profile $(PROFILE) --target $$t --dry-run || exit 1; \
	done

doctor: ## Check whether what is installed still matches this checkout
	@python3 tools/doctor.py

context: ## Report what the installed config costs in context every session
	@python3 tools/context-cost.py

# Rules reach Claude, Cursor and Antigravity only. Codex and opencode have no rules layer, so
# without this the team conventions apply in some tools and not others.
conventions: ## Regenerate the team-conventions skill from custom/rules/
	@python3 tools/build-conventions-skill.py

# Not part of `make install`: this writes to your own Claude config, which is outside
# install-state and so outside what `make uninstall` reverses. Undo is `claude mcp remove`.
# make install copies files but turns nothing on. This turns it on. Separate from install
# because it writes your own config, which make uninstall cannot reverse.
setup-user: ## Turn the shared config on for you: permissions, 2 hooks, no AI attribution, conventions for codex/opencode
	@python3 tools/setup-user.py

mcp: ## Activate the agreed MCP servers: make mcp [GCP_PROJECT=x] [ENV_FILE=path]
	@GCP_PROJECT="$(GCP_PROJECT)" python3 tools/mcp-setup.py \
		$(if $(ENV_FILE),--env-file "$(ENV_FILE)",)

# The gate CI runs, runnable locally in one word. Same commands, same order, so a green
# `make check` means a green PR. The one CI job not here is the gitleaks scan of the full
# history; the pre-commit gitleaks hook covers the files as they are.
check: ## Run every check CI runs (hooks, tests, then the overlay against the pinned upstream)
	@command -v pre-commit >/dev/null 2>&1 || { \
		echo "pre-commit not found — run 'make setup' first"; exit 1; }
	python3 tools/validate-manifests.py
	pre-commit run --all-files
	@$(MAKE) -s test
	python3 tools/materialize.py
	python3 tools/validate-manifests.py
	python3 tools/check-profile.py

# tools/ sits on every member's install path, so a bug there breaks everyone at once.
# Needs requirements-dev.txt; no network, no .ecc/.
test: ## Run the tools/ unit tests (pip install -r requirements-dev.txt first)
	python3 -m pytest -q

# The installer overwrites and adds, but never removes. So content dropped from custom/
# lingers in ~ indefinitely — and a stale rule file is still loaded into every session.
# This is the only way to get a clean fan-out.
reinstall: ## Wipe the materialized checkout and install from scratch (clears stale files)
	$(MAKE) uninstall || true
	$(MAKE) clean
	$(MAKE) install

# Bumping upstream is deliberate and reviewed — never automatic. This does the safe part
# and stops, leaving the judgement to you.
bump: ## Show what changing the pin would do, without changing it
	@echo "==> pinned SHA in upstream.json:"
	@python3 -c "import json;print('   ',json.load(open('upstream.json'))['upstream']['sha'])"
	@echo "==> newest upstream main:"
	@git ls-remote https://github.com/affaan-m/ECC.git refs/heads/main 2>/dev/null \
		| awk 'NR==1{print "    "$$1}' || echo "    (could not reach upstream)"
	@echo
	@echo "To bump: edit the sha in upstream.json, then run"
	@echo "  make validate && make plan && make context"
	@echo "Read the diff before committing. Never track main. See UPSTREAM.md."

uninstall: ## Remove everything this installed (only files recorded in install-state)
	node $(ECC)/scripts/uninstall.js

update: ## Pull the latest shared config and reinstall
	git pull --ff-only
	python3 tools/materialize.py
	@$(MAKE) -s opencode-payload
	@for t in $(TARGETS); do \
		echo "==> $$t"; $(ECC)/install.sh --profile $(PROFILE) --enable-hooks --target $$t || exit 1; \
	done
	@python3 tools/setup-user.py --restore


validate: ## Check the pin, the overlay and custom/ are consistent
	python3 tools/validate-manifests.py

audit: ## Scan the installed config with AgentShield (separate tool, runs locally)
	npx agentshield

clean: ## Remove the materialized upstream checkout
	rm -rf $(ECC)
