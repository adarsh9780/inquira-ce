package artifactbrowser

import (
	"context"
	"encoding/json"
	"os"
	"strings"

	"inquira-go/internal/apperror"
	"inquira-go/internal/conversation"
)

type store interface {
	GetArtifact(context.Context, string) (conversation.Artifact, error)
	ListArtifacts(context.Context, string) ([]conversation.Artifact, error)
	ListWorkspaceArtifacts(context.Context, string) ([]conversation.Artifact, error)
	ArtifactPath(context.Context, string) (string, error)
	DeleteArtifact(context.Context, string) error
}

type gateway interface {
	Inspect(context.Context, string) (InspectResult, error)
	Rows(context.Context, string, RowsRequest) (RowsResult, error)
}

type Service struct {
	store   store
	gateway gateway
}

func NewService(store store, gateway gateway) *Service {
	return &Service{store: store, gateway: gateway}
}

func (s *Service) ListTurn(ctx context.Context, conversationID, turnID, kind string) (ListResponse, error) {
	items, err := s.store.ListArtifacts(ctx, strings.TrimSpace(turnID))
	if err != nil {
		return ListResponse{}, err
	}
	filtered := items[:0]
	for _, item := range items {
		if item.ConversationID == strings.TrimSpace(conversationID) && (strings.TrimSpace(kind) == "" || item.Kind == strings.TrimSpace(kind)) {
			filtered = append(filtered, item)
		}
	}
	return s.summaries(ctx, filtered)
}

func (s *Service) ListWorkspace(ctx context.Context, workspaceID, kind string) (ListResponse, error) {
	items, err := s.store.ListWorkspaceArtifacts(ctx, strings.TrimSpace(workspaceID))
	if err != nil {
		return ListResponse{}, err
	}
	filtered := items[:0]
	for _, item := range items {
		if item.WorkspaceID == strings.TrimSpace(workspaceID) && (strings.TrimSpace(kind) == "" || item.Kind == strings.TrimSpace(kind)) {
			filtered = append(filtered, item)
		}
	}
	return s.summaries(ctx, filtered)
}

func (s *Service) summaries(ctx context.Context, items []conversation.Artifact) (ListResponse, error) {
	result := ListResponse{Artifacts: make([]Summary, 0, len(items))}
	for _, item := range items {
		summary := Summary{ArtifactID: item.ID, LogicalName: item.LogicalName, DisplayName: item.DisplayName, Kind: item.Kind, ByteSize: item.ByteSize, CreatedAt: item.CreatedAt, Status: item.Status}
		if item.Kind == "dataframe" && item.Status == conversation.ArtifactStatusActive {
			path, err := s.store.ArtifactPath(ctx, item.ID)
			if err != nil {
				return ListResponse{}, err
			}
			inspection, err := s.gateway.Inspect(ctx, path)
			if err != nil {
				return ListResponse{}, apperror.Wrap("artifact_inspect_failed", "Could not inspect the dataframe artifact.", err)
			}
			summary.RowCount = inspection.RowCount
			summary.Schema = inspection.Schema
			summary.Columns = inspection.Schema
		}
		result.Artifacts = append(result.Artifacts, summary)
	}
	result.Total = len(result.Artifacts)
	return result, nil
}

func (s *Service) MetadataForTurn(ctx context.Context, conversationID, turnID, artifactID string) (Metadata, error) {
	artifact, err := s.owned(ctx, artifactID, "", conversationID, turnID)
	if err != nil {
		return Metadata{}, err
	}
	return s.metadata(ctx, artifact)
}

func (s *Service) MetadataForWorkspace(ctx context.Context, workspaceID, artifactID string) (Metadata, error) {
	artifact, err := s.owned(ctx, artifactID, workspaceID, "", "")
	if err != nil {
		return Metadata{}, err
	}
	return s.metadata(ctx, artifact)
}

func (s *Service) owned(ctx context.Context, artifactID, workspaceID, conversationID, turnID string) (conversation.Artifact, error) {
	artifact, err := s.store.GetArtifact(ctx, strings.TrimSpace(artifactID))
	if err != nil {
		return conversation.Artifact{}, err
	}
	if workspaceID != "" && artifact.WorkspaceID != workspaceID || conversationID != "" && artifact.ConversationID != conversationID || turnID != "" && artifact.TurnID != turnID {
		return conversation.Artifact{}, apperror.New("artifact_not_found", "Artifact not found.")
	}
	return artifact, nil
}

func (s *Service) metadata(ctx context.Context, artifact conversation.Artifact) (Metadata, error) {
	m := Metadata{ArtifactID: artifact.ID, WorkspaceID: artifact.WorkspaceID, ConversationID: artifact.ConversationID, TurnID: artifact.TurnID, LogicalName: artifact.LogicalName, DisplayName: artifact.DisplayName, Kind: artifact.Kind, Pointer: "artifact://" + artifact.ID, ByteSize: artifact.ByteSize, CreatedAt: artifact.CreatedAt, Status: artifact.Status}
	path, err := s.store.ArtifactPath(ctx, artifact.ID)
	if err != nil {
		return Metadata{}, err
	}
	if artifact.Kind == "dataframe" {
		inspection, err := s.gateway.Inspect(ctx, path)
		if err != nil {
			return Metadata{}, apperror.Wrap("artifact_inspect_failed", "Could not inspect the dataframe artifact.", err)
		}
		m.RowCount = inspection.RowCount
		m.Schema = inspection.Schema
		m.Columns = inspection.Schema
	} else if artifact.PayloadFormat == "json" {
		payload, err := os.ReadFile(path)
		if err != nil {
			return Metadata{}, apperror.Wrap("artifact_read_failed", "Could not read the artifact payload.", err)
		}
		var decoded any
		if err := json.Unmarshal(payload, &decoded); err != nil {
			return Metadata{}, apperror.Wrap("artifact_payload_invalid", "Artifact payload is not valid JSON.", err)
		}
		m.Payload = decoded
	}
	return m, nil
}

func (s *Service) RowsForTurn(ctx context.Context, conversationID, turnID, artifactID string, request RowsRequest) (RowsResult, error) {
	artifact, err := s.owned(ctx, artifactID, "", conversationID, turnID)
	if err != nil {
		return RowsResult{}, err
	}
	return s.rows(ctx, artifact, request)
}

func (s *Service) RowsForWorkspace(ctx context.Context, workspaceID, artifactID string, request RowsRequest) (RowsResult, error) {
	artifact, err := s.owned(ctx, artifactID, workspaceID, "", "")
	if err != nil {
		return RowsResult{}, err
	}
	return s.rows(ctx, artifact, request)
}

func (s *Service) rows(ctx context.Context, artifact conversation.Artifact, request RowsRequest) (RowsResult, error) {
	if artifact.Kind != "dataframe" || artifact.PayloadFormat != "parquet" {
		return RowsResult{}, apperror.New("artifact_kind_invalid", "Only Parquet dataframe artifacts support row paging.")
	}
	if request.Offset < 0 || request.Limit < 1 || request.Limit > 1000 {
		return RowsResult{}, apperror.New("artifact_page_invalid", "Offset must be non-negative and limit must be between 1 and 1000.")
	}
	if request.SortModel == nil {
		request.SortModel = []map[string]any{}
	}
	if request.FilterModel == nil {
		request.FilterModel = map[string]any{}
	}
	path, err := s.store.ArtifactPath(ctx, artifact.ID)
	if err != nil {
		return RowsResult{}, err
	}
	result, err := s.gateway.Rows(ctx, path, request)
	if err != nil {
		return RowsResult{}, apperror.Wrap("artifact_rows_failed", "Could not read dataframe artifact rows.", err)
	}
	result.ArtifactID = artifact.ID
	result.Name = artifact.LogicalName
	result.DisplayName = artifact.DisplayName
	if result.Columns == nil {
		result.Columns = make([]string, 0, len(result.Schema))
		for _, column := range result.Schema {
			result.Columns = append(result.Columns, column.Name)
		}
	}
	return result, nil
}

func (s *Service) DeleteForTurn(ctx context.Context, conversationID, turnID, artifactID string) (DeleteResult, error) {
	artifact, err := s.owned(ctx, artifactID, "", conversationID, turnID)
	if err != nil {
		return DeleteResult{}, err
	}
	return s.delete(ctx, artifact)
}

func (s *Service) DeleteForWorkspace(ctx context.Context, workspaceID, artifactID string) (DeleteResult, error) {
	artifact, err := s.owned(ctx, artifactID, workspaceID, "", "")
	if err != nil {
		return DeleteResult{}, err
	}
	return s.delete(ctx, artifact)
}

func (s *Service) delete(ctx context.Context, artifact conversation.Artifact) (DeleteResult, error) {
	err := s.store.DeleteArtifact(ctx, artifact.ID)
	if err != nil {
		return DeleteResult{}, err
	}
	return DeleteResult{ArtifactID: artifact.ID, Deleted: true}, nil
}

func (s *Service) Usage(ctx context.Context, workspaceID string) (Usage, error) {
	items, err := s.store.ListWorkspaceArtifacts(ctx, workspaceID)
	if err != nil {
		return Usage{}, err
	}
	result := Usage{WorkspaceID: workspaceID, ByKind: map[string]int64{}}
	for _, item := range items {
		if item.WorkspaceID != workspaceID {
			continue
		}
		result.ArtifactCount++
		result.TotalBytes += item.ByteSize
		result.ByKind[item.Kind] += item.ByteSize
	}
	return result, nil
}
