package connection

import (
	"path/filepath"
	"strings"

	"inquira-go/internal/apperror"
)

func AdapterKindForPath(path string) (AdapterKind, error) {
	base := filepath.Base(strings.TrimSpace(path))
	if base == "" || strings.HasPrefix(base, ".") {
		return "", apperror.New("adapter_not_supported", "Select a supported local data file.")
	}
	switch strings.ToLower(filepath.Ext(base)) {
	case ".csv":
		return AdapterCSV, nil
	case ".parquet":
		return AdapterParquet, nil
	case ".xlsx":
		return AdapterExcel, nil
	case ".json", ".jsonl", ".ndjson":
		return AdapterJSON, nil
	case ".sqlite", ".sqlite3", ".db":
		return AdapterSQLite, nil
	default:
		return "", apperror.New("adapter_not_supported", "Supported formats are CSV, Parquet, XLSX, JSON, JSONL, NDJSON, and SQLite.")
	}
}

func supportedAdapter(kind AdapterKind) bool {
	return kind == AdapterCSV || kind == AdapterParquet || kind == AdapterExcel ||
		kind == AdapterJSON || kind == AdapterSQLite
}

func expectedExtensions(kind AdapterKind) []string {
	if kind == AdapterCSV {
		return []string{".csv"}
	}
	if kind == AdapterParquet {
		return []string{".parquet"}
	}
	if kind == AdapterExcel {
		return []string{".xlsx"}
	}
	if kind == AdapterJSON {
		return []string{".json", ".jsonl", ".ndjson"}
	}
	if kind == AdapterSQLite {
		return []string{".sqlite", ".sqlite3", ".db"}
	}
	return nil
}

func adapterAcceptsExtension(kind AdapterKind, extension string) bool {
	for _, expected := range expectedExtensions(kind) {
		if extension == expected {
			return true
		}
	}
	return false
}
