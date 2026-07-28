package connection

import "testing"

func TestAdapterKindForPathSupportsTheFirstFileAdapters(t *testing.T) {
	tests := map[string]AdapterKind{
		"sales.csv": AdapterCSV, "SALES.CSV": AdapterCSV,
		"events.parquet": AdapterParquet, "EVENTS.PARQUET": AdapterParquet,
		"workbook.xlsx": AdapterExcel, "WORKBOOK.XLSX": AdapterExcel,
		"records.json": AdapterJSON, "EVENTS.JSONL": AdapterJSON, "logs.NDJSON": AdapterJSON,
		"warehouse.sqlite": AdapterSQLite, "cache.SQLITE3": AdapterSQLite, "legacy.DB": AdapterSQLite,
	}
	for path, expected := range tests {
		kind, err := AdapterKindForPath(path)
		if err != nil || kind != expected {
			t.Fatalf("AdapterKindForPath(%q) = %q, %v", path, kind, err)
		}
	}
}

func TestAdapterKindForPathRejectsAmbiguousOrFutureFormats(t *testing.T) {
	for _, path := range []string{"data", ".csv", "data.csv.gz", "book.xls", "data.txt", "archive.duckdb"} {
		if _, err := AdapterKindForPath(path); appErrorCode(err) != "adapter_not_supported" {
			t.Fatalf("AdapterKindForPath(%q) error = %v", path, err)
		}
	}
}
