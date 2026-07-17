package workspace

const maxNameLength = 120

type Workspace struct {
	ID            string `json:"id"`
	Name          string `json:"name"`
	IsActive      bool   `json:"is_active"`
	DuckDBPath    string `json:"duckdb_path"`
	SchemaContext string `json:"schema_context"`
	CreatedAt     string `json:"created_at"`
	UpdatedAt     string `json:"updated_at"`
}

type ListResponse struct {
	Workspaces []Workspace `json:"workspaces"`
}

type CreateRequest struct {
	Name          string `json:"name"`
	SchemaContext string `json:"schema_context"`
}

type UpdateRequest struct {
	WorkspaceID   string  `json:"workspace_id"`
	Name          string  `json:"name"`
	SchemaContext *string `json:"schema_context"`
}

type Summary struct {
	ID                string   `json:"id"`
	Name              string   `json:"name"`
	IsActive          bool     `json:"is_active"`
	SchemaContext     string   `json:"schema_context"`
	CreatedAt         string   `json:"created_at"`
	UpdatedAt         string   `json:"updated_at"`
	TableCount        int      `json:"table_count"`
	TableNames        []string `json:"table_names"`
	ConversationCount int      `json:"conversation_count"`
}

type DeletionResult struct {
	JobID        string  `json:"job_id"`
	WorkspaceID  string  `json:"workspace_id"`
	Status       string  `json:"status"`
	ErrorMessage *string `json:"error_message"`
	CreatedAt    string  `json:"created_at"`
	UpdatedAt    string  `json:"updated_at"`
}
