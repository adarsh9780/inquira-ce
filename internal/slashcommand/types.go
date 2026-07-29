package slashcommand

import (
	"encoding/json"

	"github.com/adarsh9780/inquira-ce/internal/datacatalog"
)

const (
	defaultRowLimit = 500
	maxRowLimit     = 2000
)

type ExecuteRequest struct {
	WorkspaceID    string `json:"workspace_id"`
	ConversationID string `json:"conversation_id"`
	Text           string `json:"text"`
	Name           string `json:"name"`
	RawArgs        string `json:"raw_args"`
	DefaultTable   string `json:"default_table"`
	RowLimit       int    `json:"row_limit"`
}

type CompileRequest struct {
	Text         string                        `json:"text"`
	Name         string                        `json:"name"`
	RawArgs      string                        `json:"raw_args"`
	DefaultTable string                        `json:"default_table"`
	RowLimit     int                           `json:"row_limit"`
	Columns      []datacatalog.WorkspaceColumn `json:"columns"`
}

type CompiledCommand struct {
	Name       string          `json:"name"`
	Output     string          `json:"output"`
	ResultType string          `json:"result_type"`
	Result     json.RawMessage `json:"result,omitempty"`
	Truncated  bool            `json:"truncated"`
	PythonCode string          `json:"python_code"`
}

type ExecuteResult struct {
	Command        string          `json:"command"`
	Name           string          `json:"name"`
	Output         string          `json:"output"`
	ResultType     string          `json:"result_type"`
	Result         json.RawMessage `json:"result"`
	Truncated      bool            `json:"truncated"`
	ConversationID string          `json:"conversation_id"`
	TurnID         string          `json:"turn_id"`
}
