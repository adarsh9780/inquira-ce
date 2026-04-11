SHELL := /bin/bash

VERSION ?=
POS_VERSION := $(word 2,$(MAKECMDGOALS))
EFFECTIVE_VERSION := $(if $(VERSION),$(VERSION),$(POS_VERSION))
INLINE_GIT_COMMIT_MESSAGE := $(strip $(filter-out git-commit,$(MAKECMDGOALS)))

.PHONY: help help-push check-version check-version-pretty check-message check-input-version check-input-version-greater check-version-file set-version test test-pretty ruff-test ruff-test-pretty mypy-test mypy-test-pretty test-backend test-backend-pretty test-frontend test-frontend-pretty test-e2e build build-frontend sync-frontend-dist build-wheel git-add git-commit git-push push

help:
	@echo "Usage:"
	@echo "  make test"
	@echo "  make test-pretty"
	@echo "  make ruff-test"
	@echo "  make ruff-test-pretty"
	@echo "  make mypy-test"
	@echo "  make mypy-test-pretty"
	@echo "  make test-backend-pretty"
	@echo "  make test-frontend-pretty"
	@echo "  make test-e2e"
	@echo "  make check-version-pretty"
	@echo "  make build"
	@echo "  make build-frontend"
	@echo "  make sync-frontend-dist"
	@echo "  make build-wheel"
	@echo "  make git-add"
	@echo "  make git-commit"
	@echo "  make git-push"
	@echo "  make set-version 0.5.24"
	@echo "  make check-version"
	@echo "  make push"
	@echo ""
	@echo "Targets:"
	@echo "  help               Show available commands"
	@echo "  help-push          Show details for push workflow"
	@echo "  set-version        Update VERSION and apply across backend/frontend/tauri source files"
	@echo "  check-version      Print current versions from source-owned version files"
	@echo "  check-version-pretty Pretty formatted version check output (rich text + wrapping)"
	@echo "  test               Run backend and frontend test suites"
	@echo "  test-pretty        Run full validation suite with rich formatting, spacing, and wrapped output"
	@echo "  ruff-test          Run backend Ruff checks (CI-aligned scope)"
	@echo "  ruff-test-pretty   Rich-formatted Ruff checks"
	@echo "  mypy-test          Run backend mypy checks (CI-aligned scope)"
	@echo "  mypy-test-pretty   Rich-formatted mypy checks"
	@echo "  test-backend       Run backend pytest suite"
	@echo "  test-backend-pretty Rich-formatted backend pytest run"
	@echo "  test-frontend      Run frontend npm test suite"
	@echo "  test-frontend-pretty Rich-formatted frontend test run"
	@echo "  test-e2e           Run frontend Playwright end-to-end tests"
	@echo "  build              Build the CE desktop app with bundled uv for local desktop runs"
	@echo "  build-frontend     Build frontend assets into src/inquira/frontend/dist"
	@echo "  sync-frontend-dist Copy frontend assets to backend/app/frontend/dist for wheel packaging"
	@echo "  build-wheel        Build backend Python wheel with bundled frontend assets"
	@echo "  git-add            Stage all changes"
	@echo "  git-commit         Commit using commit_message.txt with validations"
	@echo "  git-push           Push current branch"
	@echo "  push               Validate message, test, commit, and push"

help-push:
	@echo "Manual push flow:"
	@echo "1) make test"
	@echo "2) make git-add"
	@echo "3) make git-commit"
	@echo "4) make git-push"
	@echo ""
	@echo "Shortcut: make push"
	@echo "- if there are local changes: check-message -> test -> git-add -> git-commit -> git-push"
	@echo "- if there are no local changes: git-push only"

check-message:
	@test -s commit_message.txt || (echo "commit_message.txt is missing or empty."; exit 1)
	@last_msg="$$(git log -1 --pretty=%B 2>/dev/null || true)"; \
	current_msg="$$(cat commit_message.txt)"; \
	if [ -n "$$last_msg" ] && [ "$$current_msg" = "$$last_msg" ]; then \
		echo "commit_message.txt matches the latest commit message. Please write a new message."; \
		exit 1; \
	fi

check-input-version:
	@test -n "$(EFFECTIVE_VERSION)" || (echo "Usage: make set-version 0.5.24"; exit 1)
	@uv run python scripts/maintenance/version_guard.py validate --version "$(EFFECTIVE_VERSION)"

check-input-version-greater: check-input-version check-version-file
	@uv run python scripts/maintenance/version_guard.py greater --current-file VERSION --new-version "$(EFFECTIVE_VERSION)"

check-version-file:
	@uv run python scripts/maintenance/version_guard.py validate-file --path VERSION

check-version:
	uv run python scripts/maintenance/show_versions.py

check-version-pretty:
	uv run --with rich python scripts/maintenance/pretty_make.py check-version-pretty

set-version: check-input-version-greater
	uv run python scripts/maintenance/bump_versions.py --version "$(EFFECTIVE_VERSION)" --write-version-file

test: ruff-test mypy-test test-backend test-frontend

test-pretty:
	uv run --with rich python scripts/maintenance/pretty_make.py test-pretty

ruff-test:
	cd backend && uv run --group dev ruff check app/v1 tests

ruff-test-pretty:
	uv run --with rich python scripts/maintenance/pretty_make.py ruff-test-pretty

mypy-test:
	cd backend && uv run --group dev mypy --config-file mypy.ini app/v1

mypy-test-pretty:
	uv run --with rich python scripts/maintenance/pretty_make.py mypy-test-pretty

test-backend:
	cd backend && uv run --group dev pytest

test-backend-pretty:
	uv run --with rich python scripts/maintenance/pretty_make.py test-backend-pretty

test-frontend:
	cd frontend && npm ci && npm test

test-frontend-pretty:
	uv run --with rich python scripts/maintenance/pretty_make.py test-frontend-pretty

test-e2e:
	cd frontend && npm ci && npx playwright install chromium webkit && npm run e2e

build:
	uv run python scripts/maintenance/bundle_uv.py
	cd src-tauri && cargo tauri build

build-frontend:
	cd frontend && npm ci && npm run build

sync-frontend-dist:
	@test -f src/inquira/frontend/dist/index.html || (echo "Frontend build output missing at src/inquira/frontend/dist. Run 'make build-frontend' first."; exit 1)
	rm -rf backend/app/frontend/dist
	mkdir -p backend/app/frontend
	cp -R src/inquira/frontend/dist backend/app/frontend/dist

build-wheel: build-frontend sync-frontend-dist
	cd backend && uv build --wheel

git-add:
	git add .

git-commit:
	@inline_msg='$(INLINE_GIT_COMMIT_MESSAGE)'; \
	explicit_msg='$(MESSAGE)'; \
	commit_msg="$$explicit_msg"; \
	if [ -z "$$commit_msg" ]; then \
		commit_msg="$$inline_msg"; \
	fi; \
	last_msg="$$(git log -1 --pretty=%B 2>/dev/null || true)"; \
	if [ -n "$$commit_msg" ]; then \
		if [ -n "$$last_msg" ] && [ "$$commit_msg" = "$$last_msg" ]; then \
			echo "Inline commit message matches the latest commit message. Please write a new message."; \
			exit 1; \
		fi; \
		git commit -m "$$commit_msg"; \
	else \
		test -s commit_message.txt || (echo "commit_message.txt is missing or empty."; exit 1); \
		current_msg="$$(cat commit_message.txt)"; \
		if [ -n "$$last_msg" ] && [ "$$current_msg" = "$$last_msg" ]; then \
			echo "commit_message.txt matches the latest commit message. Please write a new message."; \
			exit 1; \
		fi; \
		git commit -F commit_message.txt; \
		: > commit_message.txt; \
	fi

git-push:
	@branch="$$(git rev-parse --abbrev-ref HEAD)"; \
	git push origin "$$branch"

push:
	@if git diff --quiet && git diff --cached --quiet; then \
		echo "No local changes to commit; running git-push only."; \
		$(MAKE) --no-print-directory git-push; \
	else \
		$(MAKE) --no-print-directory check-message; \
		$(MAKE) --no-print-directory test; \
		$(MAKE) --no-print-directory git-add; \
		$(MAKE) --no-print-directory git-commit; \
		$(MAKE) --no-print-directory git-push; \
	fi

# Allow positional version args, e.g. `make set-version 0.5.24`.
%:
	@:
