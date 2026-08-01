package connection

import "context"

type AdapterKind string

const (
	AdapterCSV     AdapterKind = "csv"
	AdapterParquet AdapterKind = "parquet"
	AdapterExcel   AdapterKind = "excel"
	AdapterJSON    AdapterKind = "json"
	AdapterSQLite  AdapterKind = "sqlite"
)

const QualifiedOutputNamesOption = "_inquira_qualified_output_names"

type Status string

const (
	StatusReady          Status = "ready"
	StatusRefreshing     Status = "refreshing"
	StatusNeedsAttention Status = "needs_attention"
	StatusError          Status = "error"
)

type Column struct {
	Name     string `json:"name"`
	DataType string `json:"data_type"`
	Nullable bool   `json:"nullable"`
}

type SourceObject struct {
	ID       string         `json:"id"`
	Name     string         `json:"name"`
	Kind     string         `json:"kind"`
	Columns  []Column       `json:"columns"`
	Metadata map[string]any `json:"metadata,omitempty"`
}

type AdapterRequest struct {
	AdapterKind    AdapterKind    `json:"adapter_kind"`
	SourcePath     string         `json:"source_path"`
	SourceObjectID string         `json:"source_object_id,omitempty"`
	Options        map[string]any `json:"options,omitempty"`
}

type Discovery struct {
	AdapterKind AdapterKind    `json:"adapter_kind"`
	SourcePath  string         `json:"source_path"`
	Fingerprint string         `json:"fingerprint"`
	Objects     []SourceObject `json:"objects"`
}

type Preview struct {
	Columns   []Column         `json:"columns"`
	Rows      []map[string]any `json:"rows"`
	Truncated bool             `json:"truncated"`
}

type MaterializeRequest struct {
	AdapterKind       AdapterKind    `json:"adapter_kind"`
	SourcePath        string         `json:"source_path"`
	TargetDir         string         `json:"target_dir"`
	SelectedObjectIDs []string       `json:"selected_object_ids"`
	Options           map[string]any `json:"options,omitempty"`
}

type MaterializedOutput struct {
	SourceObjectID string   `json:"source_object_id"`
	Name           string   `json:"name"`
	RelativePath   string   `json:"relative_path"`
	Format         string   `json:"format"`
	Columns        []Column `json:"columns"`
	RowCount       int64    `json:"row_count"`
	ByteSize       int64    `json:"byte_size"`
}

type Materialization struct {
	Fingerprint string               `json:"fingerprint"`
	Outputs     []MaterializedOutput `json:"outputs"`
}

type AdapterGateway interface {
	Discover(context.Context, AdapterRequest) (Discovery, error)
	Preview(context.Context, AdapterRequest, int) (Preview, error)
	Materialize(context.Context, MaterializeRequest) (Materialization, error)
}

type Output struct {
	ID             string   `json:"id"`
	ConnectionID   string   `json:"connection_id"`
	SourceObjectID string   `json:"source_object_id"`
	Name           string   `json:"name"`
	SnapshotPath   string   `json:"snapshot_path"`
	Format         string   `json:"format"`
	Columns        []Column `json:"columns"`
	RowCount       int64    `json:"row_count"`
	ByteSize       int64    `json:"byte_size"`
}

type Connection struct {
	ID                   string         `json:"id"`
	WorkspaceID          string         `json:"workspace_id"`
	Name                 string         `json:"name"`
	AdapterKind          AdapterKind    `json:"adapter_kind"`
	SourcePath           string         `json:"source_path"`
	SourceFingerprint    string         `json:"source_fingerprint"`
	Status               Status         `json:"status"`
	ErrorMessage         string         `json:"error_message"`
	SelectedObjectIDs    []string       `json:"selected_object_ids"`
	Options              map[string]any `json:"options"`
	Outputs              []Output       `json:"outputs"`
	CreatedAt            string         `json:"created_at"`
	UpdatedAt            string         `json:"updated_at"`
	LastRefreshAttemptAt string         `json:"last_refresh_attempt_at"`
	LastRefreshSuccessAt string         `json:"last_refresh_success_at"`
}

type ListResponse struct {
	Connections []Connection `json:"connections"`
}

type RefreshFailure struct {
	ConnectionID   string `json:"connection_id"`
	ConnectionName string `json:"connection_name"`
	Code           string `json:"code"`
	Message        string `json:"message"`
}

type WorkspaceRefreshResult struct {
	WorkspaceID string           `json:"workspace_id"`
	Attempted   int              `json:"attempted"`
	Succeeded   int              `json:"succeeded"`
	Changed     int              `json:"changed"`
	Failures    []RefreshFailure `json:"failures"`
}

type CreateRequest struct {
	WorkspaceID       string         `json:"workspace_id"`
	Name              string         `json:"name"`
	AdapterKind       AdapterKind    `json:"adapter_kind"`
	SourcePath        string         `json:"source_path"`
	SelectedObjectIDs []string       `json:"selected_object_ids"`
	Options           map[string]any `json:"options,omitempty"`
}

type DiscoverRequest struct {
	AdapterKind AdapterKind    `json:"adapter_kind"`
	SourcePath  string         `json:"source_path"`
	Options     map[string]any `json:"options,omitempty"`
}

type PreviewRequest struct {
	AdapterKind    AdapterKind    `json:"adapter_kind"`
	SourcePath     string         `json:"source_path"`
	SourceObjectID string         `json:"source_object_id,omitempty"`
	Limit          int            `json:"limit"`
	Options        map[string]any `json:"options,omitempty"`
}

type DeleteResult struct {
	Deleted bool `json:"deleted"`
}

type DeleteOutputResult struct {
	Deleted           bool `json:"deleted"`
	ConnectionDeleted bool `json:"connection_deleted"`
}
