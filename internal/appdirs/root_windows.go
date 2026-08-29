//go:build windows

package appdirs

import (
	"path/filepath"
	"strings"

	"golang.org/x/sys/windows/registry"
)

const windowsRegistryPath = `Software\Inquira`

func platformConfiguredRoot() string {
	for _, hive := range []registry.Key{registry.CURRENT_USER, registry.LOCAL_MACHINE} {
		key, err := registry.OpenKey(hive, windowsRegistryPath, registry.QUERY_VALUE)
		if err != nil {
			continue
		}
		value, _, readErr := key.GetStringValue("DataRoot")
		_ = key.Close()
		if readErr == nil && strings.TrimSpace(value) != "" {
			return filepath.Clean(strings.TrimSpace(value))
		}
	}
	return ""
}
