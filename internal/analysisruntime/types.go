package analysisruntime

import (
	"encoding/json"

	"inquira-go/internal/conversation"
)

type ExecuteRequest struct {
	ConversationID string `json:"conversation_id"`
	TurnID         string `json:"turn_id"`
	Code           string `json:"code"`
	TimeoutSeconds int    `json:"timeout_seconds"`
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
	Artifacts  []ArtifactCandidate `json:"artifacts"`
	TimedOut   bool                `json:"timed_out"`
}

type WorkerEvent struct {
	Type string `json:"type"`
	Data any    `json:"data"`
}

type ExecuteResult struct {
	Success    bool                    `json:"success"`
	Stdout     string                  `json:"stdout"`
	Stderr     string                  `json:"stderr"`
	Error      string                  `json:"error"`
	Result     json.RawMessage         `json:"result"`
	ResultKind string                  `json:"result_kind"`
	Artifacts  []conversation.Artifact `json:"artifacts"`
	TimedOut   bool                    `json:"timed_out"`
}

type KernelStatus struct {
	WorkspaceID string `json:"workspace_id"`
	Status      string `json:"status"`
}
