package schemageneration

import (
	"github.com/adarsh9780/inquira-ce/internal/datacatalog"
	"github.com/adarsh9780/inquira-ce/internal/modelconfig"
)

type RegenerateRequest struct {
	WorkspaceID string  `json:"workspace_id"`
	TableName   string  `json:"table_name"`
	Context     *string `json:"context,omitempty"`
}

type InputColumn struct {
	Name     string `json:"name"`
	DataType string `json:"dtype"`
	Nullable bool   `json:"nullable"`
}

type GeneratedColumn struct {
	Name        string   `json:"name"`
	Description string   `json:"description"`
	Aliases     []string `json:"aliases"`
}

type GenerateRequest struct {
	WorkspaceID string                           `json:"workspace_id"`
	TableName   string                           `json:"table_name"`
	Context     string                           `json:"context"`
	Columns     []InputColumn                    `json:"columns"`
	Model       modelconfig.RuntimeConfiguration `json:"model"`
}

type GenerateResult struct {
	Columns []GeneratedColumn `json:"columns"`
}

type RegenerateResult = datacatalog.DatasetSchema
