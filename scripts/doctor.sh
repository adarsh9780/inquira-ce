#!/bin/sh

set -eu

expected_go="$1"
expected_node="$2"
expected_python="$3"
expected_uv="$4"
wails_path="$5"
failed=0

require_command() {
	name="$1"
	if ! command -v "$name" >/dev/null 2>&1; then
		printf 'missing: %s\n' "$name"
		failed=1
	fi
}

for command_name in git go node npm uv gh; do
	require_command "$command_name"
done

if [ "$failed" -ne 0 ]; then
	exit "$failed"
fi

actual_go="$(go env GOVERSION | sed 's/^go//')"
actual_node="$(node --version | sed 's/^v//')"
actual_uv="$(uv --version | awk '{print $2}')"

printf 'Go:      %s (expected %s)\n' "$actual_go" "$expected_go"
printf 'Node.js: %s (expected %s)\n' "$actual_node" "$expected_node"
printf 'Python:  %s (project expects %s)\n' "$(uv run --project python/data_worker --no-sync python -c 'import platform; print(platform.python_version())')" "$expected_python"
printf 'UV:      %s (bundled release %s)\n' "$actual_uv" "$expected_uv"

if [ -x "$wails_path" ]; then
	printf 'Wails:   %s\n' "$("$wails_path" version 2>/dev/null | head -n 1)"
else
	printf 'missing: Wails CLI at %s\n' "$wails_path"
	failed=1
fi

if [ "$actual_go" != "$expected_go" ]; then
	printf 'warning: Go will use the go.mod toolchain directive when commands run in this repository.\n'
fi
if [ "$actual_node" != "$expected_node" ]; then
	printf 'warning: activate Node.js %s from .node-version for release-equivalent checks.\n' "$expected_node"
fi
if [ "$actual_uv" != "$expected_uv" ]; then
	printf 'warning: local UV differs from the binary bundled into the application.\n'
fi

exit "$failed"
