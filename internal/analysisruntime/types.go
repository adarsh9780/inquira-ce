package analysisruntime

import (
	"encoding/json"

	"github.com/adarsh9780/inquira-ce/internal/conversation"
)

type Run struct {
	ID               string `json:"id"`
	StagingDirectory string `json:"staging_directory"`
}

type ExecuteRequest struct {
	ConversationID  string `json:"conversation_id"`
	TurnID          string `json:"turn_id"`
	Code            string `json:"code"`
	TimeoutSeconds  int    `json:"timeout_seconds"`
	AssistantText   string `json:"assistant_text,omitempty"`
	MetadataJSON    string `json:"metadata_json,omitempty"`
	UseResultOutput bool   `json:"use_result_output,omitempty"`
}

type ExecuteWorkerRequest struct {
	WorkspaceID       string `json:"workspace_id"`
	DatabasePath      string `json:"database_path"`
	Code              string `json:"code"`
	RunID             string `json:"run_id"`
	ArtifactDirectory string `json:"artifact_dir"`
	TimeoutSeconds    int    `json:"timeout_seconds"`
}

type ArtifactCandidate struct {
	Kind          string `json:"kind"`
	LogicalName   string `json:"logical_name"`
	DisplayName   string `json:"display_name"`
	PayloadFormat string `json:"payload_format"`
	MediaType     string `json:"media_type"`
	SourcePath    string `json:"source_path"`
}

type ExecuteWorkerResult struct {
	Success    bool                `json:"success"`
	Stdout     string              `json:"stdout"`
	Stderr     string              `json:"stderr"`
	Error      string              `json:"error"`
	Result     json.RawMessage     `json:"result"`
	ResultKind string              `json:"result_kind"`
	ResultName string              `json:"result_name"`
	Variables  map[string]any      `json:"variables"`
	Artifacts  []ArtifactCandidate `json:"artifacts"`
	TimedOut   bool                `json:"timed_out"`
}

type WorkerEvent struct {
	Type            string `json:"type"`
	Data            any    `json:"data"`
	ClientRequestID string `json:"client_request_id,omitempty"`
	WorkspaceID     string `json:"workspace_id,omitempty"`
	ConversationID  string `json:"conversation_id,omitempty"`
	TurnID          string `json:"turn_id,omitempty"`
	RunID           string `json:"run_id,omitempty"`
}

type ExecuteResult struct {
	RunID      string                  `json:"run_id"`
	Success    bool                    `json:"success"`
	Stdout     string                  `json:"stdout"`
	Stderr     string                  `json:"stderr"`
	Error      string                  `json:"error"`
	Result     json.RawMessage         `json:"result"`
	ResultKind string                  `json:"result_kind"`
	ResultName string                  `json:"result_name"`
	Variables  map[string]any          `json:"variables"`
	Artifacts  []conversation.Artifact `json:"artifacts"`
	TimedOut   bool                    `json:"timed_out"`
}

type KernelStatus struct {
	WorkspaceID string `json:"workspace_id"`
	Status      string `json:"status"`
}
