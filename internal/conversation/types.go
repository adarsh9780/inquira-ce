package conversation

const (
	DefaultTitle = "New conversation"

	ConversationStatusActive   = "active"
	ConversationStatusDeleting = "deleting"

	TurnStatusQueued    = "queued"
	TurnStatusRunning   = "running"
	TurnStatusCompleted = "completed"
	TurnStatusFailed    = "failed"

	ArtifactStatusActive  = "active"
	ArtifactStatusMissing = "missing"

	StorageClassArtifacts   = "artifacts"
	StorageClassAttachments = "attachments"
)

type Conversation struct {
	ID          string  `json:"id"`
	WorkspaceID string  `json:"workspace_id"`
	Title       string  `json:"title"`
	Status      string  `json:"status"`
	FinalTurnID *string `json:"final_turn_id,omitempty"`
	LastTurnAt  string  `json:"last_turn_at"`
	CreatedAt   string  `json:"created_at"`
	UpdatedAt   string  `json:"updated_at"`
}

type TurnPage struct {
	Turns      []Turn `json:"turns"`
	NextCursor string `json:"next_cursor,omitempty"`
}

type UsageSummary struct {
	InputTokens  *int64   `json:"input_tokens"`
	OutputTokens *int64   `json:"output_tokens"`
	CachedTokens *int64   `json:"cached_tokens"`
	TotalTokens  *int64   `json:"total_tokens"`
	PriceUSD     *float64 `json:"price_usd"`
}

type ConversationUsage struct {
	ConversationID string       `json:"conversation_id"`
	TurnCount      int          `json:"turn_count"`
	TurnsWithUsage int          `json:"turns_with_usage"`
	Usage          UsageSummary `json:"usage"`
}

type MoveTurnRequest struct {
	ConversationID string  `json:"conversation_id"`
	TurnID         string  `json:"turn_id"`
	ParentTurnID   *string `json:"parent_turn_id"`
}

type ReorderTurnsRequest struct {
	ConversationID string   `json:"conversation_id"`
	ParentTurnID   *string  `json:"parent_turn_id"`
	TurnIDs        []string `json:"turn_ids"`
}

type DeleteTurnResult struct {
	ConversationID string   `json:"conversation_id"`
	DeletedTurnIDs []string `json:"deleted_turn_ids"`
	Deleted        bool     `json:"deleted"`
}

type FinalRerun struct {
	Conversation Conversation `json:"conversation"`
	SourceTurn   Turn         `json:"source_turn"`
	Turn         Turn         `json:"turn"`
	Code         string       `json:"code"`
}

type Turn struct {
	ID             string  `json:"id"`
	ConversationID string  `json:"conversation_id"`
	ParentTurnID   *string `json:"parent_turn_id"`
	Sequence       int     `json:"sequence"`
	SiblingOrder   int     `json:"sibling_order"`
	Status         string  `json:"status"`
	ResultKind     string  `json:"result_kind"`
	UserText       string  `json:"user_text"`
	AssistantText  string  `json:"assistant_text"`
	ToolEventsJSON string  `json:"tool_events_json"`
	MetadataJSON   string  `json:"metadata_json"`
	CodeSnapshot   string  `json:"code_snapshot"`
	ResultJSON     string  `json:"result_json"`
	ErrorMessage   string  `json:"error_message"`
	CreatedAt      string  `json:"created_at"`
	UpdatedAt      string  `json:"updated_at"`
}

type Artifact struct {
	ID             string `json:"id"`
	WorkspaceID    string `json:"workspace_id"`
	ConversationID string `json:"conversation_id"`
	TurnID         string `json:"turn_id"`
	Kind           string `json:"kind"`
	LogicalName    string `json:"logical_name"`
	DisplayName    string `json:"display_name"`
	StorageClass   string `json:"storage_class"`
	RelativePath   string `json:"relative_path"`
	PayloadFormat  string `json:"payload_format"`
	MediaType      string `json:"media_type"`
	ByteSize       int64  `json:"byte_size"`
	SHA256         string `json:"sha256"`
	Status         string `json:"status"`
	CreatedAt      string `json:"created_at"`
}

type CreateConversationRequest struct {
	WorkspaceID string `json:"workspace_id"`
	Title       string `json:"title"`
}

type CreateTurnRequest struct {
	ConversationID string  `json:"conversation_id"`
	ParentTurnID   *string `json:"parent_turn_id"`
	UserText       string  `json:"user_text"`
	MetadataJSON   string  `json:"metadata_json"`
}

type CompleteTurnRequest struct {
	TurnID         string `json:"turn_id"`
	AssistantText  string `json:"assistant_text"`
	CodeSnapshot   string `json:"code_snapshot"`
	ToolEventsJSON string `json:"tool_events_json"`
	ResultJSON     string `json:"result_json"`
	ResultKind     string `json:"result_kind"`
	MetadataJSON   string `json:"metadata_json,omitempty"`
}

type FailTurnRequest struct {
	TurnID         string `json:"turn_id"`
	AssistantText  string `json:"assistant_text"`
	CodeSnapshot   string `json:"code_snapshot"`
	ToolEventsJSON string `json:"tool_events_json"`
	ErrorMessage   string `json:"error_message"`
	MetadataJSON   string `json:"metadata_json,omitempty"`
}

type PublishArtifactRequest struct {
	ConversationID string `json:"conversation_id"`
	TurnID         string `json:"turn_id"`
	Kind           string `json:"kind"`
	LogicalName    string `json:"logical_name"`
	DisplayName    string `json:"display_name"`
	StorageClass   string `json:"storage_class"`
	PayloadFormat  string `json:"payload_format"`
	MediaType      string `json:"media_type"`
}

type DeleteResult struct {
	ConversationID string `json:"conversation_id"`
	Deleted        bool   `json:"deleted"`
	CleanupPending bool   `json:"cleanup_pending"`
}

type ReconciliationResult struct {
	WorkspaceID          string `json:"workspace_id"`
	OrphansRemoved       int    `json:"orphans_removed"`
	MissingArtifacts     int    `json:"missing_artifacts"`
	DeletedConversations int    `json:"deleted_conversations"`
	RecoveredTurns       int    `json:"recovered_turns"`
}
