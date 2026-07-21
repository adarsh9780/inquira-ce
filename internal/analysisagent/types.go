package analysisagent

import (
	"encoding/json"

	"inquira-go/internal/analysisruntime"
	"inquira-go/internal/conversation"
	"inquira-go/internal/datacatalog"
	"inquira-go/internal/modelconfig"
)

type AnalyzeRequest struct {
	ClientRequestID string            `json:"client_request_id,omitempty"`
	WorkspaceID     string            `json:"workspace_id"`
	ConversationID  string            `json:"conversation_id,omitempty"`
	ParentTurnID    *string           `json:"parent_turn_id,omitempty"`
	Question        string            `json:"question"`
	CurrentCode     string            `json:"current_code,omitempty"`
	TimeoutSeconds  int               `json:"timeout_seconds"`
	Attachments     []ImageAttachment `json:"attachments,omitempty"`
}

type ImageAttachment struct {
	AttachmentID string `json:"attachment_id"`
	MediaType    string `json:"media_type"`
	Filename     string `json:"filename"`
	DataBase64   string `json:"data_base64"`
}

type AgentWorkerRequest struct {
	ClientRequestID   string                           `json:"client_request_id"`
	WorkspaceID       string                           `json:"workspace_id"`
	ConversationID    string                           `json:"conversation_id,omitempty"`
	TurnID            string                           `json:"turn_id,omitempty"`
	DatabasePath      string                           `json:"database_path"`
	Question          string                           `json:"question"`
	CurrentCode       string                           `json:"current_code,omitempty"`
	RunID             string                           `json:"run_id"`
	ArtifactDirectory string                           `json:"artifact_dir"`
	TimeoutSeconds    int                              `json:"timeout_seconds"`
	Model             modelconfig.RuntimeConfiguration `json:"model"`
	Context           ConversationContext              `json:"context"`
	Schema            datacatalog.AnalysisSchema       `json:"schema"`
	Attachments       []ImageAttachment                `json:"attachments,omitempty"`
}

type InterventionResponse struct {
	InterventionID string `json:"intervention_id"`
	Accepted       bool   `json:"accepted"`
}

type ConversationContext struct {
	Turns []ContextTurn `json:"turns"`
}

type ContextTurn struct {
	TurnID        string            `json:"turn_id"`
	Status        string            `json:"status"`
	UserText      string            `json:"user_text"`
	AssistantText string            `json:"assistant_text,omitempty"`
	Code          string            `json:"code,omitempty"`
	ResultKind    string            `json:"result_kind,omitempty"`
	Result        json.RawMessage   `json:"result,omitempty"`
	Error         string            `json:"error,omitempty"`
	Artifacts     []ContextArtifact `json:"artifacts"`
}

type ContextArtifact struct {
	ArtifactID    string `json:"artifact_id"`
	Kind          string `json:"kind"`
	LogicalName   string `json:"logical_name"`
	DisplayName   string `json:"display_name,omitempty"`
	PayloadFormat string `json:"payload_format"`
	MediaType     string `json:"media_type,omitempty"`
	ByteSize      int64  `json:"byte_size"`
}

type AgentWorkerResult struct {
	Success   bool                                `json:"success"`
	Answer    string                              `json:"answer"`
	Code      string                              `json:"code"`
	Execution analysisruntime.ExecuteWorkerResult `json:"execution"`
	Error     string                              `json:"error"`
	Route     string                              `json:"route"`
	Metadata  map[string]any                      `json:"metadata"`
}

type AnalyzeResult struct {
	Conversation conversation.Conversation           `json:"conversation"`
	Turn         conversation.Turn                   `json:"turn"`
	Answer       string                              `json:"answer"`
	Code         string                              `json:"code"`
	RunID        string                              `json:"run_id"`
	Execution    analysisruntime.ExecuteWorkerResult `json:"execution"`
	Artifacts    []conversation.Artifact             `json:"artifacts"`
	Route        string                              `json:"route"`
	Metadata     map[string]any                      `json:"metadata"`
}
