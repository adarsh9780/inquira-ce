SHELL := /bin/sh
.DEFAULT_GOAL := help

APP_NAME := inquira-go
REPOSITORY_NAME := inquira-ce
FRONTEND_DIR := frontend
PYTHON_PROJECT := python/data_worker
VERSION_FILE := VERSION
WAILS_TEMPLATE := wails.template.json
WAILS ?= $(shell go env GOPATH)/bin/wails
UV ?= uv
NPM ?= npm

GO_VERSION := 1.26.5
NODE_VERSION := 24.18.0
PYTHON_VERSION := 3.12.13
UV_VERSION := 0.11.28
GOVULNCHECK_VERSION := v1.6.0
GITLEAKS_VERSION := v8.30.1
ACTIONLINT_VERSION := v1.7.12

GITHUB_OWNER ?= $(shell gh api user --jq .login 2>/dev/null)
GITHUB_REPOSITORY ?= $(GITHUB_OWNER)/$(REPOSITORY_NAME)
VISIBILITY ?= public
RELEASE_VERSION ?=
MACOS_INSTALLER ?=
WINDOWS_INSTALLER ?=
RELEASE_STAGE_DIR ?= release-stage
PUBLIC_DOWNLOADS_BASE_URL ?= https://downloads.inquiraai.com
PUBLIC_RELEASE_NOTES_URL ?= https://inquiraai.com/docs/getting-started/distribution

.PHONY: help doctor versions app-version bootstrap dev frontend-dev frontend-embed prepare-version prepare-uv runtime-info \
	fmt fmt-check lint lint-go lint-actions typecheck test test-go test-python test-frontend \
	test-frontend-source test-runtime test-runtime-e2e test-live-provider test-full \
	frontend-build bundle-check audit audit-go audit-python audit-frontend audit-secrets \
	ci build package release-stage release-check github-check github-publish clean

help: ## Show available development commands.
	@awk 'BEGIN {FS = ":.*## "; printf "Usage: make <target>\n\nTargets:\n"} /^[a-zA-Z0-9_.-]+:.*## / {printf "  %-24s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

doctor: ## Check required tools and report version mismatches.
	@./scripts/doctor.sh "$(GO_VERSION)" "$(NODE_VERSION)" "$(PYTHON_VERSION)" "$(UV_VERSION)" "$(WAILS)"

versions: ## Print the toolchain versions pinned by this repository.
	@printf 'Go:      %s\n' "$(GO_VERSION)"
	@printf 'Node.js: %s\n' "$(NODE_VERSION)"
	@printf 'Python:  %s\n' "$(PYTHON_VERSION)"
	@printf 'UV:      %s\n' "$(UV_VERSION)"

app-version: ## Print the canonical application version.
	@tr -d '[:space:]' < $(VERSION_FILE)
	@printf '\n'

bootstrap: ## Install locked Go, frontend, and Python development dependencies.
	go mod download
	cd $(FRONTEND_DIR) && $(NPM) ci
	$(UV) sync --project $(PYTHON_PROJECT) --locked --group dev

dev: prepare-version prepare-uv ## Start the Wails desktop development server.
	$(WAILS) dev

frontend-dev: ## Start only the frontend development server.
	cd $(FRONTEND_DIR) && $(NPM) run dev

prepare-version: ## Generate ignored desktop metadata from the canonical VERSION file.
	go run ./cmd/prepareversion -version-file "$(VERSION_FILE)" -template "$(WAILS_TEMPLATE)" -output wails.json

prepare-uv: ## Download and checksum-verify the pinned UV binary for this platform.
	go run ./cmd/prepareuv -version "$(UV_VERSION)"

runtime-info: ## Inspect the runtime bundled into an existing macOS or Windows build.
	@./scripts/runtime-info.sh "$(APP_NAME)"

fmt: ## Format tracked Go source files.
	gofmt -w $$(git ls-files '*.go')

fmt-check: ## Verify tracked Go source files are formatted.
	@unformatted="$$(gofmt -l $$(git ls-files '*.go'))"; \
	if [ -n "$$unformatted" ]; then \
		printf 'The following Go files need gofmt:\n%s\n' "$$unformatted"; \
		exit 1; \
	fi

lint: lint-go lint-actions typecheck ## Run static checks for Go, GitHub Actions, and TypeScript.

frontend-embed:
	@if [ ! -f "$(FRONTEND_DIR)/dist/index.html" ]; then \
		$(MAKE) frontend-build; \
	fi

lint-go: frontend-embed ## Run Go vet across the application.
	go vet ./...

lint-actions: ## Validate GitHub Actions workflow syntax.
	go run github.com/rhysd/actionlint/cmd/actionlint@$(ACTIONLINT_VERSION)

typecheck: ## Type-check the Vue/TypeScript frontend.
	cd $(FRONTEND_DIR) && $(NPM) run typecheck

test: test-go test-frontend test-python ## Run every deterministic unit and contract test.

test-go: frontend-embed ## Run all Go tests.
	go test ./...

test-python: ## Run the locked Python worker test suite.
	$(UV) run --project $(PYTHON_PROJECT) --locked --group dev pytest

test-frontend: ## Run all frontend source and runtime tests.
	cd $(FRONTEND_DIR) && $(NPM) test

test-frontend-source: ## Run source-level frontend contract tests.
	cd $(FRONTEND_DIR) && $(NPM) run test:source

test-runtime: ## Run browser-runtime component tests.
	cd $(FRONTEND_DIR) && $(NPM) run test:runtime

test-runtime-e2e: prepare-uv ## Exercise the production Go-to-Python runtime pipeline.
	INQUIRA_RUN_RUNTIME_E2E=1 go test -run TestProductionRuntimePipelineEndToEnd -v .

test-live-provider: ## Run opt-in tests against a configured live model provider.
	$(UV) run --project $(PYTHON_PROJECT) --locked --group dev pytest python/data_worker/tests/test_live_provider.py -v

test-full: test frontend-build test-runtime-e2e ## Run all local tests, the production build, and runtime E2E.

frontend-build: ## Build the production frontend bundle.
	cd $(FRONTEND_DIR) && $(NPM) run build

bundle-check: ## Build the frontend and enforce bundle budgets.
	cd $(FRONTEND_DIR) && $(NPM) run bundle:check

audit: audit-go audit-python audit-frontend audit-secrets ## Run dependency, vulnerability, and secret audits.

audit-go: frontend-embed ## Scan reachable Go code with the pinned govulncheck release.
	go run golang.org/x/vuln/cmd/govulncheck@$(GOVULNCHECK_VERSION) ./...

audit-python: ## Audit the active locked Python worker environment.
	$(UV) run --project $(PYTHON_PROJECT) --locked --group dev pip-audit --local --skip-editable

audit-frontend: ## Audit all frontend production and development dependencies.
	cd $(FRONTEND_DIR) && $(NPM) audit --audit-level=high

audit-secrets: ## Scan the current tree and Git history for committed secrets.
	go run github.com/zricethezav/gitleaks/v8@$(GITLEAKS_VERSION) git --redact --no-banner .
	go run github.com/zricethezav/gitleaks/v8@$(GITLEAKS_VERSION) dir --redact --no-banner .

ci: fmt-check lint test frontend-build audit ## Reproduce the required continuous-integration checks.

build: prepare-version prepare-uv ## Build the production Wails desktop application.
	$(WAILS) build -clean

package: build ## Build the platform package for the current host.

release-stage: ## Stage installers, checksums, and download manifests for manual release recovery.
	@test -n "$(RELEASE_VERSION)" || (echo "RELEASE_VERSION is required"; exit 1)
	@test -n "$(MACOS_INSTALLER)" || (echo "MACOS_INSTALLER is required"; exit 1)
	@test -n "$(WINDOWS_INSTALLER)" || (echo "WINDOWS_INSTALLER is required"; exit 1)
	go run ./cmd/releasemanifest \
		-version "$(RELEASE_VERSION)" \
		-macos "$(MACOS_INSTALLER)" \
		-windows "$(WINDOWS_INSTALLER)" \
		-output "$(RELEASE_STAGE_DIR)" \
		-base-url "$(PUBLIC_DOWNLOADS_BASE_URL)" \
		-release-notes-url "$(PUBLIC_RELEASE_NOTES_URL)"

release-check: ci build ## Run every local release gate.

github-check: ## Verify the repository is clean and ready for GitHub publication.
	@./scripts/github-check.sh "$(GITHUB_REPOSITORY)"

github-publish: github-check ## Create/connect the public GitHub repository and push the current branch.
	@if [ "$(CONFIRM_PUBLISH)" != "1" ]; then \
		echo "Refusing to publish without CONFIRM_PUBLISH=1"; \
		exit 1; \
	fi
	@./scripts/github-publish.sh "$(GITHUB_REPOSITORY)" "$(VISIBILITY)"

clean: ## Remove generated build and bundled-runtime outputs.
	rm -rf build/bin frontend/dist
	rm -f wails.json frontend/package.json.md5
	rm -f internal/runtimeprovision/assets/uv internal/runtimeprovision/assets/uv.exe
	rm -f internal/runtimeprovision/assets/manifest.json
