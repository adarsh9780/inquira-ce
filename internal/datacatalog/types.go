package datacatalog

import "inquira-go/internal/connection"

type TableStatus string

const (
	TableStatusReady TableStatus = "ready"
	TableStatusStale TableStatus = "stale"
)

type Table struct {
	ID             string              `json:"id"`
	ConnectionID   string              `json:"connection_id"`
	SourceObjectID string              `json:"source_object_id"`
	Name           string              `json:"name"`
	SnapshotPath   string              `json:"snapshot_path"`
	Columns        []connection.Column `json:"columns"`
	RowCount       int64               `json:"row_count"`
	Status         TableStatus         `json:"status"`
}

type Catalog struct {
	WorkspaceID  string  `json:"workspace_id"`
	DatabasePath string  `json:"database_path"`
	Fingerprint  string  `json:"fingerprint"`
	Tables       []Table `json:"tables"`
	Changed      bool    `json:"changed"`
	ByteSize     int64   `json:"byte_size"`
}

type BuildTable struct {
	ID           string `json:"id"`
	Name         string `json:"name"`
	SnapshotPath string `json:"snapshot_path"`
}

type BuildRequest struct {
	DatabasePath string       `json:"database_path"`
	Fingerprint  string       `json:"fingerprint"`
	Tables       []BuildTable `json:"tables"`
}

type BuildResult struct {
	DatabasePath string `json:"database_path"`
	Fingerprint  string `json:"fingerprint"`
	Changed      bool   `json:"changed"`
	TableCount   int    `json:"table_count"`
	ByteSize     int64  `json:"byte_size"`
}
