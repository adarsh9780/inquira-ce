#!/bin/sh

set -eu

app_name="$1"
macos_binary="build/bin/$app_name.app/Contents/MacOS/$app_name"
windows_binary="build/bin/$app_name.exe"
unix_binary="build/bin/$app_name"

for candidate in "$macos_binary" "$windows_binary" "$unix_binary"; do
	if [ -x "$candidate" ]; then
		exec "$candidate" runtime-info
	fi
done

echo "No built Inquira executable was found. Run make build first."
exit 1
