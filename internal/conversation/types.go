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
	ID          string `json:"id"`
	WorkspaceID string `json:"workspace_id"`
	Title       string `json:"title"`
	Status      string `json:"status"`
	LastTurnAt  string `json:"last_turn_at"`
	CreatedAt   string `json:"created_at"`
	UpdatedAt   string `json:"updated_at"`
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
}

type FailTurnRequest struct {
	TurnID         string `json:"turn_id"`
	AssistantText  string `json:"assistant_text"`
	CodeSnapshot   string `json:"code_snapshot"`
	ToolEventsJSON string `json:"tool_events_json"`
	ErrorMessage   string `json:"error_message"`
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
}
