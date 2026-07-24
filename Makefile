WAILS ?= $(shell go env GOPATH)/bin/wails

.PHONY: prepare-uv test test-runtime-e2e test-live-provider build clean

prepare-uv:
	go run ./cmd/prepareuv

test:
	go test ./...
	cd frontend && npm run typecheck
	cd frontend && node --test test/firstRunModelOnboarding.test.mjs test/llmConfigTabFlow.test.mjs test/workspaceAiReadinessExperience.test.mjs test/localConnectionExperience.test.mjs test/nativeTurnArtifactApi.test.mjs test/nativeCatalogCodeApi.test.mjs test/runtimeProvisioningExperience.test.mjs test/conversationUsageAndShortcuts.test.mjs test/nativeWailsTerminalIntegration.test.mjs test/nativeWailsDesktopRecovery.test.mjs test/nativeWailsExportFile.test.mjs test/nativeWailsLocalState.test.mjs test/nativeWailsUIPreferences.test.mjs test/nativeWailsRemainingParity.test.mjs
	cd frontend && node --test test/nativeAgentRuntimeContract.test.mjs
	uv run --project python/data_worker --group dev pytest
	cd frontend && npm run test:runtime
	cd frontend && npm run build

test-runtime-e2e:
	INQUIRA_RUN_RUNTIME_E2E=1 go test -run TestProductionRuntimePipelineEndToEnd -v .

test-live-provider:
	uv run --project python/data_worker --group dev pytest python/data_worker/tests/test_live_provider.py -v

build: prepare-uv
	$(WAILS) build -clean

clean:
	rm -rf build/bin frontend/dist
	rm -f internal/runtimeprovision/assets/uv internal/runtimeprovision/assets/uv.exe
	rm -f internal/runtimeprovision/assets/manifest.json
