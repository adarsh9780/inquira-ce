WAILS ?= $(shell go env GOPATH)/bin/wails

.PHONY: prepare-uv test build clean

prepare-uv:
	go run ./cmd/prepareuv

test:
	go test ./...
	cd frontend && node --test test/firstRunModelOnboarding.test.mjs test/llmConfigTabFlow.test.mjs test/workspaceAiReadinessExperience.test.mjs
	cd frontend && npm run test:runtime
	cd frontend && npm run build

build: prepare-uv
	$(WAILS) build -clean

clean:
	rm -rf build/bin frontend/dist
	rm -f internal/runtimeprovision/assets/uv internal/runtimeprovision/assets/uv.exe
	rm -f internal/runtimeprovision/assets/manifest.json
