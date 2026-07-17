package connection

import (
	"path/filepath"
	"strings"

	"inquira-go/internal/apperror"
)

func AdapterKindForPath(path string) (AdapterKind, error) {
	base := filepath.Base(strings.TrimSpace(path))
	if base == "" || strings.HasPrefix(base, ".") {
		return "", apperror.New("adapter_not_supported", "Select a CSV or Parquet file.")
	}
	switch strings.ToLower(filepath.Ext(base)) {
	case ".csv":
		return AdapterCSV, nil
	case ".parquet":
		return AdapterParquet, nil
	default:
		return "", apperror.New("adapter_not_supported", "Only CSV and Parquet connections are supported right now.")
	}
}

func supportedAdapter(kind AdapterKind) bool {
	return kind == AdapterCSV || kind == AdapterParquet
}

func expectedExtension(kind AdapterKind) string {
	if kind == AdapterCSV {
		return ".csv"
	}
	if kind == AdapterParquet {
		return ".parquet"
	}
	return ""
}
