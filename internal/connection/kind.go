package connection

import (
	"path/filepath"
	"strings"

	"inquira-go/internal/apperror"
)

func AdapterKindForPath(path string) (AdapterKind, error) {
	base := filepath.Base(strings.TrimSpace(path))
	if base == "" || strings.HasPrefix(base, ".") {
		return "", apperror.New("adapter_not_supported", "Select a CSV, Parquet, or XLSX file.")
	}
	switch strings.ToLower(filepath.Ext(base)) {
	case ".csv":
		return AdapterCSV, nil
	case ".parquet":
		return AdapterParquet, nil
	case ".xlsx":
		return AdapterExcel, nil
	default:
		return "", apperror.New("adapter_not_supported", "Only CSV, Parquet, and XLSX connections are supported right now.")
	}
}

func supportedAdapter(kind AdapterKind) bool {
	return kind == AdapterCSV || kind == AdapterParquet || kind == AdapterExcel
}

func expectedExtension(kind AdapterKind) string {
	if kind == AdapterCSV {
		return ".csv"
	}
	if kind == AdapterParquet {
		return ".parquet"
	}
	if kind == AdapterExcel {
		return ".xlsx"
	}
	return ""
}
