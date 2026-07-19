package artifactbrowser

type Column struct {
	Name string `json:"name"`
	Type string `json:"type"`
}

type InspectResult struct {
	RowCount int64    `json:"row_count"`
	Schema   []Column `json:"schema"`
	Columns  []Column `json:"columns"`
}

type RowsRequest struct {
	Offset      int              `json:"offset"`
	Limit       int              `json:"limit"`
	SortModel   []map[string]any `json:"sort_model"`
	FilterModel map[string]any   `json:"filter_model"`
	SearchText  string           `json:"search_text"`
}

type RowsResult struct {
	ArtifactID  string           `json:"artifact_id"`
	Name        string           `json:"name"`
	DisplayName string           `json:"display_name"`
	RowCount    int64            `json:"row_count"`
	Schema      []Column         `json:"schema"`
	Columns     []string         `json:"columns"`
	Rows        []map[string]any `json:"rows"`
	Offset      int              `json:"offset"`
	Limit       int              `json:"limit"`
}

type Summary struct {
	ArtifactID  string   `json:"artifact_id"`
	LogicalName string   `json:"logical_name"`
	DisplayName string   `json:"display_name"`
	Kind        string   `json:"kind"`
	RowCount    int64    `json:"row_count,omitempty"`
	Schema      []Column `json:"schema,omitempty"`
	Columns     []Column `json:"columns,omitempty"`
	ByteSize    int64    `json:"byte_size"`
	CreatedAt   string   `json:"created_at"`
	Status      string   `json:"status"`
}

type ListResponse struct {
	Artifacts []Summary `json:"artifacts"`
	Total     int       `json:"total"`
}

type Metadata struct {
	ArtifactID     string   `json:"artifact_id"`
	WorkspaceID    string   `json:"workspace_id"`
	ConversationID string   `json:"conversation_id"`
	TurnID         string   `json:"turn_id"`
	LogicalName    string   `json:"logical_name"`
	DisplayName    string   `json:"display_name"`
	Kind           string   `json:"kind"`
	Pointer        string   `json:"pointer"`
	Schema         []Column `json:"schema,omitempty"`
	Columns        []Column `json:"columns,omitempty"`
	RowCount       int64    `json:"row_count,omitempty"`
	Payload        any      `json:"payload,omitempty"`
	ByteSize       int64    `json:"byte_size"`
	CreatedAt      string   `json:"created_at"`
	Status         string   `json:"status"`
}

type DeleteResult struct {
	ArtifactID string `json:"artifact_id"`
	Deleted    bool   `json:"deleted"`
}

type Usage struct {
	WorkspaceID   string           `json:"workspace_id"`
	ArtifactCount int              `json:"artifact_count"`
	TotalBytes    int64            `json:"total_bytes"`
	ByKind        map[string]int64 `json:"by_kind"`
}
