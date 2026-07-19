package analysisagent

import (
	"inquira-go/internal/analysisruntime"
	"inquira-go/internal/conversation"
	"inquira-go/internal/modelconfig"
)

type AnalyzeRequest struct {
	WorkspaceID    string  `json:"workspace_id"`
	ConversationID string  `json:"conversation_id,omitempty"`
	ParentTurnID   *string `json:"parent_turn_id,omitempty"`
	Question       string  `json:"question"`
	TimeoutSeconds int     `json:"timeout_seconds"`
}

type AgentWorkerRequest struct {
	WorkspaceID       string                           `json:"workspace_id"`
	DatabasePath      string                           `json:"database_path"`
	Question          string                           `json:"question"`
	RunID             string                           `json:"run_id"`
	ArtifactDirectory string                           `json:"artifact_dir"`
	TimeoutSeconds    int                              `json:"timeout_seconds"`
	Model             modelconfig.RuntimeConfiguration `json:"model"`
}

type AgentWorkerResult struct {
	Success   bool                                `json:"success"`
	Answer    string                              `json:"answer"`
	Code      string                              `json:"code"`
	Execution analysisruntime.ExecuteWorkerResult `json:"execution"`
	Error     string                              `json:"error"`
}

type AnalyzeResult struct {
	Conversation conversation.Conversation           `json:"conversation"`
	Turn         conversation.Turn                   `json:"turn"`
	Answer       string                              `json:"answer"`
	Code         string                              `json:"code"`
	RunID        string                              `json:"run_id"`
	Execution    analysisruntime.ExecuteWorkerResult `json:"execution"`
	Artifacts    []conversation.Artifact             `json:"artifacts"`
}
