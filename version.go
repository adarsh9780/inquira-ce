package main

import (
	_ "embed"
	"strings"
)

// applicationVersionSource is the canonical application version embedded in
// the Go backend at compile time.
//
//go:embed VERSION
var applicationVersionSource string

func applicationVersion() string {
	return strings.TrimSpace(applicationVersionSource)
}

// GetApplicationVersion exposes the same canonical version to native clients
// and diagnostics without introducing a second backend constant.
func (a *App) GetApplicationVersion() string {
	return applicationVersion()
}
