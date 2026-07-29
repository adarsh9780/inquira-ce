package datacatalog

import "github.com/adarsh9780/inquira-ce/internal/connection"

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
	SourcePath     string              `json:"source_path"`
	FileType       string              `json:"file_type"`
	SnapshotPath   string              `json:"-"`
	Columns        []connection.Column `json:"columns"`
	RowCount       int64               `json:"row_count"`
	Status         TableStatus         `json:"status"`
	CreatedAt      string              `json:"created_at"`
	UpdatedAt      string              `json:"updated_at"`
}

type Catalog struct {
	WorkspaceID    string         `json:"workspace_id"`
	DatabasePath   string         `json:"database_path"`
	Fingerprint    string         `json:"fingerprint"`
	Tables         []Table        `json:"tables"`
	AnalysisSchema AnalysisSchema `json:"analysis_schema"`
	Changed        bool           `json:"changed"`
	ByteSize       int64          `json:"byte_size"`
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

type Dataset struct {
	ID             string `json:"id"`
	WorkspaceID    string `json:"workspace_id"`
	ConnectionID   string `json:"connection_id"`
	SourceObjectID string `json:"source_object_id"`
	SourcePath     string `json:"source_path"`
	TableName      string `json:"table_name"`
	RowCount       int64  `json:"row_count"`
	FileType       string `json:"file_type"`
	SchemaStatus   string `json:"schema_status"`
	CreatedAt      string `json:"created_at"`
	UpdatedAt      string `json:"updated_at"`
}

type DatasetListResponse struct {
	Datasets []Dataset `json:"datasets"`
}

type SchemaColumn struct {
	Name        string   `json:"name"`
	DataType    string   `json:"dtype"`
	Type        string   `json:"type"`
	Nullable    bool     `json:"nullable"`
	Description string   `json:"description"`
	Aliases     []string `json:"aliases"`
}

type DatasetSchema struct {
	TableName string         `json:"table_name"`
	Context   string         `json:"context"`
	Columns   []SchemaColumn `json:"columns"`
}

type AnalysisTable struct {
	Name    string         `json:"name"`
	Columns []SchemaColumn `json:"columns"`
}

type AnalysisSchema struct {
	Context string          `json:"context"`
	Tables  []AnalysisTable `json:"tables"`
}

type SaveSchemaRequest struct {
	WorkspaceID string         `json:"workspace_id"`
	TableName   string         `json:"table_name"`
	Context     *string        `json:"context,omitempty"`
	Columns     []SchemaColumn `json:"columns"`
}

type ColumnOverride struct {
	Name        string   `json:"name"`
	Description string   `json:"description"`
	Aliases     []string `json:"aliases"`
}

type WorkspaceColumn struct {
	TableName  string `json:"table_name"`
	ColumnName string `json:"column_name"`
	DataType   string `json:"dtype"`
}
