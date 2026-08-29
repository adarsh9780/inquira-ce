//go:build !windows

package appdirs

func platformConfiguredRoot() string { return "" }
