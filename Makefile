SHELL := /bin/bash

VERSION ?=
POS_VERSION := $(word 2,$(MAKECMDGOALS))
EFFECTIVE_VERSION := $(if $(VERSION),$(VERSION),$(POS_VERSION))
UV_VERSION := 0.6.3

.PHONY: help help-release help-push help-tag check-version check-version-pretty check-message check-input-version check-input-version-greater check-version-file check-no-version-arg check-tag-not-latest check-uv-version stage-bundled-uv-local set-version metadata test test-pretty ruff-test ruff-test-pretty mypy-test mypy-test-pretty test-backend test-backend-pretty test-frontend test-frontend-pretty build-frontend sync-frontend-dist build-wheel build-desktop git-add git-commit git-push git-tag push release

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
	@echo "  make check-version-pretty"
	@echo "  make build-frontend"
	@echo "  make sync-frontend-dist"
	@echo "  make build-wheel"
	@echo "  make build-desktop"
	@echo "  make git-add"
	@echo "  make git-commit"
	@echo "  make git-push"
	@echo "  make set-version 0.5.24"
	@echo "  make check-version"
	@echo "  make check-uv-version"
	@echo "  make metadata"
	@echo "  make git-tag"
	@echo "  make push"
	@echo "  make release"
	@echo ""
	@echo "Targets:"
	@echo "  help          Show available commands"
	@echo "  help-push     Show details for push workflow"
	@echo "  help-release  Show details for release workflow"
	@echo "  help-tag      Show details for tag workflow"
	@echo "  set-version   Update VERSION and apply across backend/frontend/tauri/installers"
	@echo "  check-version Print current versions from all version-bearing files"
	@echo "  check-uv-version Ensure local uv version matches pinned release version"
	@echo "  check-version-pretty Pretty formatted version check output (rich text + wrapping)"
	@echo "  metadata      Regenerate .github/release/metadata.json from release_metadata.md"
	@echo "  test          Run backend and frontend test suites"
	@echo "  test-pretty   Run full validation suite with rich formatting, spacing, and wrapped output"
	@echo "  ruff-test     Run backend Ruff checks (CI-aligned scope)"
	@echo "  ruff-test-pretty Rich-formatted Ruff checks"
	@echo "  mypy-test     Run backend mypy checks (CI-aligned scope)"
	@echo "  mypy-test-pretty Rich-formatted mypy checks"
	@echo "  test-backend  Run backend pytest suite"
	@echo "  test-backend-pretty Rich-formatted backend pytest run"
	@echo "  test-frontend Run frontend npm test suite"
	@echo "  test-frontend-pretty Rich-formatted frontend test run"
	@echo "  build-frontend Build frontend assets into src/inquira/frontend/dist"
	@echo "  sync-frontend-dist Copy frontend assets to backend/app/frontend/dist for wheel packaging"
	@echo "  build-wheel   Build backend Python wheel with bundled frontend assets"
	@echo "  build-desktop Build desktop app via Tauri (Tauri runs frontend build via beforeBuildCommand)"
	@echo "  git-add       Stage all changes"
	@echo "  git-commit    Commit using commit_message.txt with validations"
	@echo "  git-push      Push current branch"
	@echo "  git-tag       Create and push annotated tag from VERSION"
	@echo "  push          Validate message, test, commit, and push"
	@echo "  release       metadata -> test -> commit -> push -> tag"

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

help-release:
	@echo "Release flow:"
	@echo "1) make set-version X.Y.Z"
	@echo "2) make metadata"
	@echo "3) make test"
	@echo "4) make git-add"
	@echo "5) make git-commit"
	@echo "6) make git-push"
	@echo "7) make git-tag"
	@echo ""
	@echo "Shortcut: make release"
	@echo "Runs (fail-fast): metadata -> test -> git-add -> git-commit -> git-push -> git-tag"
	@echo "Requirements: set-version must be greater than current VERSION, and commit_message.txt must be fresh."

help-tag:
	@echo "make git-tag"
	@echo "Creates and pushes annotated tag using VERSION file."
	@echo "Fails if a version argument is provided or if VERSION equals the latest tag."

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

check-no-version-arg:
	@test -z "$(VERSION)" && test -z "$(POS_VERSION)" || (echo "Do not pass a version to this target. Version is read from VERSION."; exit 1)

check-version:
	uv run python scripts/maintenance/show_versions.py

check-version-pretty:
	uv run --with rich python scripts/maintenance/pretty_make.py check-version-pretty

check-tag-not-latest: check-no-version-arg check-version-file
	@file_version="$$(tr -d '[:space:]' < VERSION)"; \
	tag="v$$file_version"; \
	last_tag="$$(git describe --tags --abbrev=0 2>/dev/null || true)"; \
	if [ -n "$$last_tag" ] && [ "$$last_tag" = "$$tag" ]; then \
		echo "Tag $$tag matches the latest existing tag. Use a newer version."; \
		exit 1; \
	fi

check-uv-version:
	@uv run python scripts/maintenance/check_uv_version.py --expected "$(UV_VERSION)"

stage-bundled-uv-local: check-uv-version
	@uv run python scripts/maintenance/stage_bundled_uv.py

set-version: check-input-version-greater
	uv run python scripts/maintenance/bump_versions.py --version "$(EFFECTIVE_VERSION)" --write-version-file

metadata: check-version-file
	@if [ -f release_metadata.md ]; then \
		uv run python scripts/maintenance/generate_release_metadata.py; \
	else \
		echo "release_metadata.md not found; skipping metadata generation."; \
	fi

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

build-frontend:
	cd frontend && npm ci && npm run build

sync-frontend-dist:
	@test -f src/inquira/frontend/dist/index.html || (echo "Frontend build output missing at src/inquira/frontend/dist. Run 'make build-frontend' first."; exit 1)
	rm -rf backend/app/frontend/dist
	mkdir -p backend/app/frontend
	cp -R src/inquira/frontend/dist backend/app/frontend/dist

build-wheel: build-frontend sync-frontend-dist
	cd backend && uv build --wheel

build-desktop: stage-bundled-uv-local
	cd frontend && npm ci
	cargo tauri build

git-add:
	git add .

git-commit: check-message
	git commit -F commit_message.txt
	: > commit_message.txt

git-push:
	@branch="$$(git rev-parse --abbrev-ref HEAD)"; \
	git push origin "$$branch"

git-tag: check-no-version-arg check-version-file check-tag-not-latest
	@file_version="$$(tr -d '[:space:]' < VERSION)"; \
	tag="v$$file_version"; \
	git tag -a "$$tag" -m "Release $$tag"; \
	git push origin "$$tag"

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

release: check-no-version-arg check-version-file metadata test git-add git-commit git-push git-tag

# Allow positional version args, e.g. `make set-version 0.5.24`.
%:
	@:
