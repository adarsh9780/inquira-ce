ifeq ($(OS),Windows_NT)
SHELL := bash
else
SHELL := /bin/bash
endif

VERSION ?=
POS_VERSION := $(word 2,$(MAKECMDGOALS))
EFFECTIVE_VERSION := $(if $(VERSION),$(VERSION),$(POS_VERSION))
msg ?=
MSG ?=
file ?=
FILE ?=
tag ?=
TAG ?=

ifneq ($(filter setv bump-all tag,$(MAKECMDGOALS)),)
%:
	@:
endif

.PHONY: help status check doctor verify-version check-version check-version-pretty check-input-version check-input-version-greater check-version-file setv bump-all test test-fast test-slow test-pretty ruff-test ruff-test-pretty mypy-test mypy-test-pretty test-backend test-backend-pretty test-agent test-rust test-frontend test-frontend-pretty test-e2e test-packaged-smoke dev build build-frontend sync-frontend-dist build-wheel commit push tag

help:
	@echo "Usage:"
	@echo "  make dev"
	@echo "  make build"
	@echo "  make setv 0.5.24"
	@echo "  make test"
	@echo "  make check"
	@echo "  make check-version"
	@echo "  make doctor"
	@echo "  make status"
	@echo "  make commit msg='fix: describe the change'"
	@echo "  make commit file=commit_message.txt"
	@echo "  make push"
	@echo "  make tag tag=v0.5.24"
	@echo ""
	@echo "Targets:"
	@echo "  help               Show available commands"
	@echo "  status             Show CE git status"
	@echo "  check              Run required validation suites and verify aligned versions"
	@echo "  doctor             Run the broad CE health check"
	@echo "  verify-version     Fail if source-owned version files are not aligned"
	@echo "  check-version      Print current versions from source-owned version files"
	@echo "  check-version-pretty Pretty formatted version check output (rich text + wrapping)"
	@echo "  setv               Update VERSION and apply across backend/frontend/tauri source files"
	@echo "  test               Run all fast required validation suites and frontend build"
	@echo "  test-fast          Run required PR validation suites"
	@echo "  test-slow          Run browser E2E tests"
	@echo "  test-pretty        Run full validation suite with rich formatting, spacing, and wrapped output"
	@echo "  ruff-test          Run backend Ruff checks (CI-aligned scope)"
	@echo "  ruff-test-pretty   Rich-formatted Ruff checks"
	@echo "  mypy-test          Run backend mypy checks (CI-aligned scope)"
	@echo "  mypy-test-pretty   Rich-formatted mypy checks"
	@echo "  test-backend       Run backend pytest suite"
	@echo "  test-agent         Run external agent runtime tests"
	@echo "  test-rust          Run Tauri/Rust tests"
	@echo "  test-backend-pretty Rich-formatted backend pytest run"
	@echo "  test-frontend      Run frontend npm test suite"
	@echo "  test-frontend-pretty Rich-formatted frontend test run"
	@echo "  test-e2e           Run frontend Playwright end-to-end tests"
	@echo "  test-packaged-smoke Require a packaged app path for smoke test handoff"
	@echo "  dev                Run frontend Vite dev server and cargo tauri dev"
	@echo "  build              Build the CE desktop app with bundled uv for local desktop runs"
	@echo "  build-frontend     Build frontend assets into src/inquira/frontend/dist"
	@echo "  sync-frontend-dist Copy frontend assets to backend/app/frontend/dist for wheel packaging"
	@echo "  build-wheel        Build backend Python wheel with bundled frontend assets"
	@echo "  commit             Stage all changes and commit with msg=... or file=..."
	@echo "  push               Push current branch"
	@echo "  tag                Create and push an annotated CE source tag"

status:
	@uv run python scripts/maintenance/ce_ops.py status

check: test-fast verify-version

doctor:
	uv run python scripts/maintenance/ce_ops.py doctor

check-input-version:
	@test -n "$(EFFECTIVE_VERSION)" || (echo "Usage: make setv 0.5.24"; exit 1)
	@uv run python scripts/maintenance/version_guard.py validate --version "$(EFFECTIVE_VERSION)"

check-input-version-greater: check-input-version check-version-file
	@uv run python scripts/maintenance/version_guard.py greater --current-file VERSION --new-version "$(EFFECTIVE_VERSION)"

check-version-file:
	@uv run python scripts/maintenance/version_guard.py validate-file --path VERSION

verify-version:
	uv run python scripts/maintenance/show_versions.py --verify

check-version:
	uv run python scripts/maintenance/show_versions.py

check-version-pretty:
	uv run --with rich python scripts/maintenance/pretty_make.py check-version-pretty

setv: check-input-version-greater
	uv run python scripts/maintenance/bump_versions.py --version "$(EFFECTIVE_VERSION)" --write-version-file

bump-all: setv

test: test-fast

test-fast: ruff-test mypy-test test-backend test-agent test-rust test-frontend build-frontend

test-slow: test-e2e

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

test-agent:
	uv run --project agents --with pytest --with pytest-asyncio pytest agents/tests

test-rust:
	cd src-tauri && cargo test

test-backend-pretty:
	uv run --with rich python scripts/maintenance/pretty_make.py test-backend-pretty

test-frontend:
	cd frontend && npm ci && npm test

test-frontend-pretty:
	uv run --with rich python scripts/maintenance/pretty_make.py test-frontend-pretty

test-e2e:
	cd frontend && npm ci && npx playwright install chromium webkit && npm run e2e

test-packaged-smoke:
	@echo "Packaged desktop smoke tests require a built installer and platform runner."
	@test -n "$(INQUIRA_PACKAGED_APP)" || (echo "Set INQUIRA_PACKAGED_APP to the packaged application path."; exit 1)

dev:
	uv run python scripts/maintenance/ce_ops.py dev

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

commit:
	@uv run python scripts/maintenance/ce_ops.py commit --msg "$(or $(msg),$(MSG))" --file "$(or $(file),$(FILE))"

push:
	@uv run python scripts/maintenance/ce_ops.py push

tag:
	@release_tag="$(or $(tag),$(TAG),$(EFFECTIVE_VERSION))"; \
	test -n "$$release_tag" || (echo "Usage: make tag tag=vX.Y.Z"; exit 1); \
	uv run python scripts/maintenance/ce_ops.py tag --tag "$$release_tag"
