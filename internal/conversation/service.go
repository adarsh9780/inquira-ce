package conversation

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/google/uuid"

	"inquira-go/internal/apperror"
)

const maxTitleLength = 255

type repository interface {
	WorkspaceExists(context.Context, string) (bool, error)
	CreateConversation(context.Context, Conversation) error
	GetConversation(context.Context, string, bool) (Conversation, error)
	ListConversations(context.Context, string, bool) ([]Conversation, error)
	WorkspaceIDs(context.Context) ([]string, error)
	MarkConversationDeleting(context.Context, string, string) error
	PurgeConversation(context.Context, string) error
	CreateTurn(context.Context, Turn) (Turn, error)
	GetTurn(context.Context, string) (Turn, error)
	ListTurns(context.Context, string) ([]Turn, error)
	CompleteTurn(context.Context, Turn) (Turn, error)
	FailTurn(context.Context, Turn) (Turn, error)
	CreateArtifact(context.Context, Artifact) error
	GetArtifact(context.Context, string) (Artifact, error)
	ListArtifacts(context.Context, string) ([]Artifact, error)
	ListConversationArtifacts(context.Context, string) ([]Artifact, error)
	SetArtifactStatus(context.Context, string, string) error
	Close() error
}

type Service struct {
	repository repository
	heap       heap
	now        func() time.Time
	newID      func() string
}

func NewService(repository repository, heap heap) *Service {
	return &Service{repository: repository, heap: heap, now: time.Now, newID: uuid.NewString}
}

func (s *Service) CreateConversation(ctx context.Context, request CreateConversationRequest) (Conversation, error) {
	workspaceID := strings.TrimSpace(request.WorkspaceID)
	if workspaceID == "" {
		return Conversation{}, apperror.New("workspace_required", "Choose a workspace before creating a conversation.")
	}
	if !safePathComponent(workspaceID) {
		return Conversation{}, apperror.New("workspace_invalid", "Workspace storage identity is invalid.")
	}
	exists, err := s.repository.WorkspaceExists(ctx, workspaceID)
	if err != nil {
		return Conversation{}, apperror.Wrap("workspace_read_failed", "Could not verify the workspace.", err)
	}
	if !exists {
		return Conversation{}, apperror.New("workspace_not_found", "Workspace not found.")
	}
	title, err := normalizeTitle(request.Title)
	if err != nil {
		return Conversation{}, err
	}
	now := formatTime(s.now().UTC())
	conversation := Conversation{
		ID: s.newID(), WorkspaceID: workspaceID, Title: title, Status: ConversationStatusActive,
		CreatedAt: now, UpdatedAt: now,
	}
	if !safePathComponent(conversation.ID) {
		return Conversation{}, apperror.New("conversation_identity_invalid", "Could not create a safe conversation identity.")
	}
	if err := s.heap.CreateConversation(workspaceID, conversation.ID); err != nil {
		return Conversation{}, apperror.Wrap("conversation_heap_failed", "Could not prepare conversation storage.", err)
	}
	if err := s.repository.CreateConversation(ctx, conversation); err != nil {
		_ = s.heap.RemoveConversation(workspaceID, conversation.ID)
		return Conversation{}, apperror.Wrap("conversation_create_failed", "Could not create the conversation.", err)
	}
	return conversation, nil
}

func (s *Service) ListConversations(ctx context.Context, workspaceID string) ([]Conversation, error) {
	id := strings.TrimSpace(workspaceID)
	if id == "" {
		return nil, apperror.New("workspace_required", "Choose a workspace before listing conversations.")
	}
	conversations, err := s.repository.ListConversations(ctx, id, false)
	if err != nil {
		return nil, apperror.Wrap("conversation_list_failed", "Could not load conversations.", err)
	}
	return conversations, nil
}

func (s *Service) CreateTurn(ctx context.Context, request CreateTurnRequest) (Turn, error) {
	conversationID := strings.TrimSpace(request.ConversationID)
	if conversationID == "" {
		return Turn{}, apperror.New("conversation_required", "Choose a conversation before asking a question.")
	}
	userText := strings.TrimSpace(request.UserText)
	if userText == "" {
		return Turn{}, apperror.New("turn_user_text_required", "Enter a question before creating a turn.")
	}
	metadata, err := normalizeJSONObject(request.MetadataJSON, "turn_metadata_invalid", "Turn metadata must be a JSON object.")
	if err != nil {
		return Turn{}, err
	}
	var parent *string
	if request.ParentTurnID != nil {
		id := strings.TrimSpace(*request.ParentTurnID)
		if id == "" {
			return Turn{}, apperror.New("turn_parent_not_found", "Parent turn not found in this conversation.")
		}
		parent = &id
	}
	now := formatTime(s.now().UTC())
	turn, err := s.repository.CreateTurn(ctx, Turn{
		ID: s.newID(), ConversationID: conversationID, ParentTurnID: parent,
		Status: TurnStatusQueued, UserText: userText, ToolEventsJSON: "[]", MetadataJSON: metadata,
		CreatedAt: now, UpdatedAt: now,
	})
	if errors.Is(err, errConversationNotFound) {
		return Turn{}, apperror.New("conversation_not_found", "Conversation not found.")
	}
	if errors.Is(err, errParentTurnNotFound) {
		return Turn{}, apperror.New("turn_parent_not_found", "Parent turn not found in this conversation.")
	}
	if err != nil {
		return Turn{}, apperror.Wrap("turn_create_failed", "Could not create the conversation turn.", err)
	}
	return turn, nil
}

func (s *Service) ListTurns(ctx context.Context, conversationID string) ([]Turn, error) {
	id := strings.TrimSpace(conversationID)
	if id == "" {
		return nil, apperror.New("conversation_required", "Choose a conversation before listing turns.")
	}
	turns, err := s.repository.ListTurns(ctx, id)
	if errors.Is(err, errConversationNotFound) {
		return nil, apperror.New("conversation_not_found", "Conversation not found.")
	}
	if err != nil {
		return nil, apperror.Wrap("turn_list_failed", "Could not load conversation turns.", err)
	}
	return turns, nil
}

func (s *Service) CompleteTurn(ctx context.Context, request CompleteTurnRequest) (Turn, error) {
	turnID := strings.TrimSpace(request.TurnID)
	if turnID == "" {
		return Turn{}, apperror.New("turn_required", "Turn identity is required.")
	}
	toolEvents, err := normalizeJSONArray(request.ToolEventsJSON, "turn_tools_invalid", "Turn tool events must be a JSON array.")
	if err != nil {
		return Turn{}, err
	}
	result, err := normalizeJSONValue(request.ResultJSON, "turn_result_invalid", "Turn result must be valid JSON.")
	if err != nil {
		return Turn{}, err
	}
	updated, err := s.repository.CompleteTurn(ctx, Turn{
		ID: turnID, AssistantText: request.AssistantText, CodeSnapshot: request.CodeSnapshot,
		ToolEventsJSON: toolEvents, ResultJSON: result, ResultKind: strings.TrimSpace(request.ResultKind),
		UpdatedAt: formatTime(s.now().UTC()),
	})
	return s.turnUpdateResult(updated, err)
}

func (s *Service) FailTurn(ctx context.Context, request FailTurnRequest) (Turn, error) {
	turnID := strings.TrimSpace(request.TurnID)
	if turnID == "" {
		return Turn{}, apperror.New("turn_required", "Turn identity is required.")
	}
	toolEvents, err := normalizeJSONArray(request.ToolEventsJSON, "turn_tools_invalid", "Turn tool events must be a JSON array.")
	if err != nil {
		return Turn{}, err
	}
	message := strings.TrimSpace(request.ErrorMessage)
	if message == "" {
		return Turn{}, apperror.New("turn_error_required", "A failed turn must include an error message.")
	}
	updated, err := s.repository.FailTurn(ctx, Turn{
		ID: turnID, AssistantText: request.AssistantText, CodeSnapshot: request.CodeSnapshot,
		ToolEventsJSON: toolEvents, ErrorMessage: message, UpdatedAt: formatTime(s.now().UTC()),
	})
	return s.turnUpdateResult(updated, err)
}

func (s *Service) PublishArtifact(ctx context.Context, request PublishArtifactRequest, source io.Reader) (Artifact, error) {
	conversationID := strings.TrimSpace(request.ConversationID)
	if conversationID == "" {
		return Artifact{}, apperror.New("conversation_required", "Conversation identity is required for an artifact.")
	}
	turnID := strings.TrimSpace(request.TurnID)
	if turnID == "" {
		return Artifact{}, apperror.New("turn_required", "Turn identity is required for an artifact.")
	}
	kind := strings.ToLower(strings.TrimSpace(request.Kind))
	if kind == "" {
		return Artifact{}, apperror.New("artifact_kind_required", "Artifact kind is required.")
	}
	logicalName := strings.TrimSpace(request.LogicalName)
	if logicalName == "" {
		return Artifact{}, apperror.New("artifact_name_required", "Artifact name is required.")
	}
	format := strings.TrimPrefix(strings.ToLower(strings.TrimSpace(request.PayloadFormat)), ".")
	if !safeToken(format) {
		return Artifact{}, apperror.New("artifact_format_invalid", "Artifact format must contain only lowercase letters and numbers.")
	}
	storageClass := strings.ToLower(strings.TrimSpace(request.StorageClass))
	if storageClass == "" {
		storageClass = StorageClassArtifacts
	}
	if !validStorageClass(storageClass) {
		return Artifact{}, apperror.New("artifact_storage_class_invalid", "Artifact storage class is invalid.")
	}
	conversation, err := s.repository.GetConversation(ctx, conversationID, false)
	if errors.Is(err, errConversationNotFound) {
		return Artifact{}, apperror.New("conversation_not_found", "Conversation not found.")
	}
	if err != nil {
		return Artifact{}, apperror.Wrap("conversation_read_failed", "Could not load the artifact conversation.", err)
	}
	turn, err := s.repository.GetTurn(ctx, turnID)
	if errors.Is(err, errTurnNotFound) || (err == nil && turn.ConversationID != conversationID) {
		return Artifact{}, apperror.New("turn_not_found", "Turn not found in this conversation.")
	}
	if err != nil {
		return Artifact{}, apperror.Wrap("turn_read_failed", "Could not load the artifact turn.", err)
	}
	artifactID := s.newID()
	object, err := s.heap.Put(conversation.WorkspaceID, conversation.ID, storageClass, artifactID, format, source)
	if err != nil {
		return Artifact{}, apperror.Wrap("artifact_write_failed", "Could not write the artifact payload.", err)
	}
	artifact := Artifact{
		ID: artifactID, WorkspaceID: conversation.WorkspaceID, ConversationID: conversation.ID, TurnID: turn.ID,
		Kind: kind, LogicalName: logicalName, DisplayName: strings.TrimSpace(request.DisplayName),
		StorageClass: storageClass, RelativePath: object.RelativePath, PayloadFormat: format,
		MediaType: strings.TrimSpace(request.MediaType), ByteSize: object.ByteSize, SHA256: object.SHA256,
		Status: ArtifactStatusActive, CreatedAt: formatTime(s.now().UTC()),
	}
	if err := s.repository.CreateArtifact(ctx, artifact); err != nil {
		_ = s.heap.RemoveObject(conversation.WorkspaceID, object.RelativePath)
		return Artifact{}, apperror.Wrap("artifact_index_failed", "Could not index the artifact payload.", err)
	}
	return artifact, nil
}

func (s *Service) ListArtifacts(ctx context.Context, turnID string) ([]Artifact, error) {
	id := strings.TrimSpace(turnID)
	if id == "" {
		return nil, apperror.New("turn_required", "Turn identity is required.")
	}
	artifacts, err := s.repository.ListArtifacts(ctx, id)
	if errors.Is(err, errTurnNotFound) {
		return nil, apperror.New("turn_not_found", "Turn not found.")
	}
	if err != nil {
		return nil, apperror.Wrap("artifact_list_failed", "Could not load turn artifacts.", err)
	}
	return artifacts, nil
}

func (s *Service) ArtifactPath(ctx context.Context, artifactID string) (string, error) {
	artifact, err := s.repository.GetArtifact(ctx, strings.TrimSpace(artifactID))
	if errors.Is(err, errArtifactNotFound) {
		return "", apperror.New("artifact_not_found", "Artifact not found.")
	}
	if err != nil {
		return "", apperror.Wrap("artifact_read_failed", "Could not load artifact metadata.", err)
	}
	if artifact.Status == ArtifactStatusMissing {
		return "", apperror.New("artifact_payload_missing", "Artifact payload is missing from local storage.")
	}
	if !validArtifactPointer(artifact) {
		return "", apperror.New("artifact_path_invalid", "Artifact path is invalid.")
	}
	path, err := s.heap.Resolve(artifact.WorkspaceID, artifact.RelativePath)
	if err != nil {
		return "", apperror.Wrap("artifact_path_invalid", "Artifact path is invalid.", err)
	}
	info, err := os.Stat(path)
	if err != nil || !info.Mode().IsRegular() {
		_ = s.repository.SetArtifactStatus(ctx, artifact.ID, ArtifactStatusMissing)
		return "", apperror.New("artifact_payload_missing", "Artifact payload is missing from local storage.")
	}
	return path, nil
}

func (s *Service) DeleteConversation(ctx context.Context, conversationID string) (DeleteResult, error) {
	id := strings.TrimSpace(conversationID)
	conversation, err := s.repository.GetConversation(ctx, id, false)
	if errors.Is(err, errConversationNotFound) {
		return DeleteResult{}, apperror.New("conversation_not_found", "Conversation not found.")
	}
	if err != nil {
		return DeleteResult{}, apperror.Wrap("conversation_read_failed", "Could not load the conversation.", err)
	}
	if err := s.repository.MarkConversationDeleting(ctx, id, formatTime(s.now().UTC())); err != nil {
		return DeleteResult{}, apperror.Wrap("conversation_delete_failed", "Could not mark the conversation for deletion.", err)
	}
	if err := s.heap.RemoveConversation(conversation.WorkspaceID, conversation.ID); err != nil {
		return DeleteResult{ConversationID: id, CleanupPending: true}, apperror.Wrap(
			"conversation_cleanup_pending", "Conversation was deleted but its local files still require cleanup.", err,
		)
	}
	if err := s.repository.PurgeConversation(ctx, id); err != nil {
		return DeleteResult{ConversationID: id, CleanupPending: true}, apperror.Wrap(
			"conversation_cleanup_pending", "Conversation was deleted but its index still requires cleanup.", err,
		)
	}
	return DeleteResult{ConversationID: id, Deleted: true}, nil
}

func (s *Service) ReconcileWorkspace(ctx context.Context, workspaceID string) (ReconciliationResult, error) {
	id := strings.TrimSpace(workspaceID)
	if id == "" || !safePathComponent(id) {
		return ReconciliationResult{}, apperror.New("workspace_invalid", "Workspace storage identity is invalid.")
	}
	conversations, err := s.repository.ListConversations(ctx, id, true)
	if err != nil {
		return ReconciliationResult{}, apperror.Wrap("reconciliation_index_failed", "Could not load conversation storage references.", err)
	}
	result := ReconciliationResult{WorkspaceID: id}
	referenced := make(map[string]map[string]struct{})
	artifactsByPath := make(map[string]Artifact)
	invalidArtifacts := make([]Artifact, 0)
	for _, conversation := range conversations {
		if conversation.Status == ConversationStatusDeleting {
			if err := s.heap.RemoveConversation(id, conversation.ID); err != nil {
				return result, apperror.Wrap("reconciliation_cleanup_failed", "Could not finish deleting conversation files.", err)
			}
			if err := s.repository.PurgeConversation(ctx, conversation.ID); err != nil {
				return result, apperror.Wrap("reconciliation_index_failed", "Could not finish deleting the conversation index.", err)
			}
			result.DeletedConversations++
			continue
		}
		references := make(map[string]struct{})
		artifacts, err := s.repository.ListConversationArtifacts(ctx, conversation.ID)
		if err != nil {
			return result, apperror.Wrap("reconciliation_index_failed", "Could not load artifact references.", err)
		}
		for _, artifact := range artifacts {
			if !validArtifactPointer(artifact) {
				invalidArtifacts = append(invalidArtifacts, artifact)
				continue
			}
			references[artifact.RelativePath] = struct{}{}
			artifactsByPath[artifact.RelativePath] = artifact
		}
		referenced[conversation.ID] = references
	}
	heapResult, err := s.heap.ReconcileWorkspace(id, referenced)
	if err != nil {
		return result, apperror.Wrap("reconciliation_heap_failed", "Could not reconcile conversation files.", err)
	}
	missing := make(map[string]struct{}, len(heapResult.MissingPaths))
	for _, artifact := range invalidArtifacts {
		if artifact.Status != ArtifactStatusMissing {
			if err := s.repository.SetArtifactStatus(ctx, artifact.ID, ArtifactStatusMissing); err != nil {
				return result, apperror.Wrap("reconciliation_index_failed", "Could not mark an invalid artifact pointer.", err)
			}
		}
	}
	for _, path := range heapResult.MissingPaths {
		missing[path] = struct{}{}
		if artifact, exists := artifactsByPath[path]; exists && artifact.Status != ArtifactStatusMissing {
			if err := s.repository.SetArtifactStatus(ctx, artifact.ID, ArtifactStatusMissing); err != nil {
				return result, apperror.Wrap("reconciliation_index_failed", "Could not mark a missing artifact.", err)
			}
		}
	}
	for path, artifact := range artifactsByPath {
		if _, isMissing := missing[path]; !isMissing && artifact.Status == ArtifactStatusMissing {
			if err := s.repository.SetArtifactStatus(ctx, artifact.ID, ArtifactStatusActive); err != nil {
				return result, apperror.Wrap("reconciliation_index_failed", "Could not restore an artifact reference.", err)
			}
		}
	}
	result.OrphansRemoved = heapResult.OrphansRemoved
	result.MissingArtifacts = len(heapResult.MissingPaths) + len(invalidArtifacts)
	return result, nil
}

func (s *Service) ReconcileAll(ctx context.Context) ([]ReconciliationResult, error) {
	workspaceIDs, err := s.repository.WorkspaceIDs(ctx)
	if err != nil {
		return nil, apperror.Wrap("reconciliation_index_failed", "Could not load workspaces for reconciliation.", err)
	}
	results := make([]ReconciliationResult, 0, len(workspaceIDs))
	for _, workspaceID := range workspaceIDs {
		result, err := s.ReconcileWorkspace(ctx, workspaceID)
		if err != nil {
			return nil, err
		}
		results = append(results, result)
	}
	return results, nil
}

func (s *Service) Close() error { return s.repository.Close() }

func (s *Service) turnUpdateResult(turn Turn, err error) (Turn, error) {
	if errors.Is(err, errTurnNotFound) {
		return Turn{}, apperror.New("turn_not_found", "Turn not found.")
	}
	if errors.Is(err, errTurnStateInvalid) {
		return Turn{}, apperror.New("turn_state_invalid", "Turn is already in a terminal state.")
	}
	if err != nil {
		return Turn{}, apperror.Wrap("turn_update_failed", "Could not update the conversation turn.", err)
	}
	return turn, nil
}

func normalizeTitle(value string) (string, error) {
	title := strings.TrimSpace(value)
	if title == "" {
		title = DefaultTitle
	}
	if len([]rune(title)) > maxTitleLength {
		return "", apperror.New("conversation_title_too_long", fmt.Sprintf("Conversation title must be %d characters or fewer.", maxTitleLength))
	}
	return title, nil
}

func normalizeJSONObject(value, code, message string) (string, error) {
	trimmed := strings.TrimSpace(value)
	if trimmed == "" {
		return "{}", nil
	}
	var decoded map[string]any
	if err := json.Unmarshal([]byte(trimmed), &decoded); err != nil || decoded == nil {
		return "", apperror.New(code, message)
	}
	return trimmed, nil
}

func normalizeJSONArray(value, code, message string) (string, error) {
	trimmed := strings.TrimSpace(value)
	if trimmed == "" {
		return "[]", nil
	}
	var decoded []any
	if err := json.Unmarshal([]byte(trimmed), &decoded); err != nil || decoded == nil {
		return "", apperror.New(code, message)
	}
	return trimmed, nil
}

func normalizeJSONValue(value, code, message string) (string, error) {
	trimmed := strings.TrimSpace(value)
	if trimmed == "" {
		return "", nil
	}
	if !json.Valid([]byte(trimmed)) {
		return "", apperror.New(code, message)
	}
	return trimmed, nil
}

func validArtifactPointer(artifact Artifact) bool {
	if !safePathComponent(artifact.ConversationID) || !safePathComponent(artifact.ID) ||
		!validStorageClass(artifact.StorageClass) || !safeToken(artifact.PayloadFormat) {
		return false
	}
	expected := strings.Join([]string{
		"conversations", artifact.ConversationID, artifact.StorageClass,
		artifact.ID + "." + artifact.PayloadFormat,
	}, "/")
	return filepath.ToSlash(filepath.Clean(filepath.FromSlash(artifact.RelativePath))) == expected
}

func formatTime(value time.Time) string { return value.UTC().Format(time.RFC3339Nano) }
