package connection

import (
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/google/uuid"

	"inquira-go/internal/apperror"
)

const maxConnectionNameLength = 120

type repository interface {
	WorkspaceExists(context.Context, string) (bool, error)
	Create(context.Context, Connection, string) error
	Get(context.Context, string) (Connection, error)
	List(context.Context, string) ([]Connection, error)
	ReplaceSnapshot(context.Context, Connection) error
	MarkRefreshing(context.Context, string, string) error
	MarkReady(context.Context, string, string) error
	MarkNeedsAttention(context.Context, string, string, string) error
	MarkError(context.Context, string, string, string) error
	Delete(context.Context, string) error
	Close() error
}

type Service struct {
	repository   repository
	gateway      AdapterGateway
	snapshotRoot string
	now          func() time.Time
	locks        sync.Map
}

func NewService(repository repository, gateway AdapterGateway, snapshotRoot string) *Service {
	return &Service{repository: repository, gateway: gateway, snapshotRoot: snapshotRoot, now: time.Now}
}

func (s *Service) Discover(ctx context.Context, request DiscoverRequest) (Discovery, error) {
	sourcePath, err := validateSource(request.AdapterKind, request.SourcePath)
	if err != nil {
		return Discovery{}, err
	}
	discovery, err := s.gateway.Discover(ctx, AdapterRequest{
		AdapterKind: request.AdapterKind, SourcePath: sourcePath, Options: request.Options,
	})
	if err != nil {
		return Discovery{}, apperror.Wrap("connection_discovery_failed", "Could not inspect the selected source.", err)
	}
	return discovery, nil
}

func (s *Service) Preview(ctx context.Context, request PreviewRequest) (Preview, error) {
	if request.Limit < 1 || request.Limit > 1000 {
		return Preview{}, apperror.New("invalid_preview_limit", "Preview limit must be between 1 and 1000.")
	}
	sourcePath, err := validateSource(request.AdapterKind, request.SourcePath)
	if err != nil {
		return Preview{}, err
	}
	preview, err := s.gateway.Preview(ctx, AdapterRequest{
		AdapterKind: request.AdapterKind, SourcePath: sourcePath,
		SourceObjectID: strings.TrimSpace(request.SourceObjectID), Options: request.Options,
	}, request.Limit)
	if err != nil {
		return Preview{}, apperror.Wrap("connection_preview_failed", "Could not preview the selected source.", err)
	}
	return preview, nil
}

func (s *Service) Create(ctx context.Context, request CreateRequest) (Connection, error) {
	workspaceID := strings.TrimSpace(request.WorkspaceID)
	if workspaceID == "" {
		return Connection{}, apperror.New("workspace_required", "Select a workspace before creating a connection.")
	}
	exists, err := s.repository.WorkspaceExists(ctx, workspaceID)
	if err != nil {
		return Connection{}, apperror.Wrap("workspace_lookup_failed", "Could not validate the workspace.", err)
	}
	if !exists {
		return Connection{}, apperror.New("workspace_not_found", "Workspace not found.")
	}
	name, normalizedName, err := validateName(request.Name)
	if err != nil {
		return Connection{}, err
	}
	sourcePath, err := validateSource(request.AdapterKind, request.SourcePath)
	if err != nil {
		return Connection{}, err
	}
	selected, err := validateSelection(request.SelectedObjectIDs)
	if err != nil {
		return Connection{}, err
	}
	connectionID := uuid.NewString()
	snapshotID := uuid.NewString()
	staging, final := s.snapshotPaths(workspaceID, connectionID, snapshotID)
	if err := os.MkdirAll(filepath.Dir(staging), 0o700); err != nil {
		return Connection{}, apperror.Wrap("snapshot_create_failed", "Could not prepare local snapshot storage.", err)
	}
	cleanupRoot := filepath.Join(s.snapshotRoot, workspaceID, connectionID)
	materialization, err := s.gateway.Materialize(ctx, MaterializeRequest{
		AdapterKind: request.AdapterKind, SourcePath: sourcePath, TargetDir: staging,
		SelectedObjectIDs: selected, Options: request.Options,
	})
	if err != nil {
		_ = os.RemoveAll(cleanupRoot)
		return Connection{}, apperror.Wrap("connection_create_failed", "Could not create the local snapshot.", err)
	}
	outputs, err := validateAndPublish(connectionID, staging, final, materialization, selected)
	if err != nil {
		_ = os.RemoveAll(cleanupRoot)
		return Connection{}, err
	}
	now := formatTime(s.now())
	connection := Connection{
		ID: connectionID, WorkspaceID: workspaceID, Name: name,
		AdapterKind: request.AdapterKind, SourcePath: sourcePath,
		SourceFingerprint: materialization.Fingerprint, Status: StatusReady,
		SelectedObjectIDs: selected, Options: cloneOptions(request.Options), Outputs: outputs,
		CreatedAt: now, UpdatedAt: now, LastRefreshAttemptAt: now, LastRefreshSuccessAt: now,
	}
	if err := s.repository.Create(ctx, connection, normalizedName); err != nil {
		_ = os.RemoveAll(cleanupRoot)
		if isUniqueConstraint(err) {
			return Connection{}, apperror.New("connection_name_exists", "A connection with this name already exists in the workspace.")
		}
		return Connection{}, apperror.Wrap("connection_create_failed", "Could not save the connection.", err)
	}
	return connection, nil
}

func (s *Service) Refresh(ctx context.Context, connectionID string) (Connection, error) {
	id := strings.TrimSpace(connectionID)
	lock := s.connectionLock(id)
	lock.Lock()
	defer lock.Unlock()

	connection, err := s.Get(ctx, id)
	if err != nil {
		return Connection{}, err
	}
	attemptedAt := formatTime(s.now())
	if err := s.repository.MarkRefreshing(ctx, id, attemptedAt); err != nil {
		return Connection{}, apperror.Wrap("connection_refresh_failed", "Could not start the refresh.", err)
	}
	discovery, err := s.gateway.Discover(ctx, AdapterRequest{
		AdapterKind: connection.AdapterKind, SourcePath: connection.SourcePath, Options: connection.Options,
	})
	if err != nil {
		s.recordRefreshError(ctx, id, attemptedAt, err)
		return Connection{}, apperror.Wrap("connection_refresh_failed", "Could not inspect the source during refresh.", err)
	}
	if discovery.Fingerprint == connection.SourceFingerprint {
		if err := s.repository.MarkReady(ctx, id, attemptedAt); err != nil {
			return Connection{}, apperror.Wrap("connection_refresh_failed", "Could not finish the refresh.", err)
		}
		return s.Get(ctx, id)
	}
	if missing := missingSelectedObjects(discovery.Objects, connection.SelectedObjectIDs); len(missing) > 0 {
		message := "A selected source object no longer exists. Recreate the connection to choose its replacement."
		_ = s.repository.MarkNeedsAttention(ctx, id, message, attemptedAt)
		return Connection{}, apperror.New("connection_needs_attention", message)
	}
	snapshotID := uuid.NewString()
	staging, final := s.snapshotPaths(connection.WorkspaceID, connection.ID, snapshotID)
	if err := os.MkdirAll(filepath.Dir(staging), 0o700); err != nil {
		s.recordRefreshError(ctx, id, attemptedAt, err)
		return Connection{}, apperror.Wrap("connection_refresh_failed", "Could not prepare refresh storage.", err)
	}
	materialization, err := s.gateway.Materialize(ctx, MaterializeRequest{
		AdapterKind: connection.AdapterKind, SourcePath: connection.SourcePath,
		TargetDir: staging, SelectedObjectIDs: connection.SelectedObjectIDs, Options: connection.Options,
	})
	if err != nil {
		_ = os.RemoveAll(staging)
		s.recordRefreshError(ctx, id, attemptedAt, err)
		return Connection{}, apperror.Wrap("connection_refresh_failed", "Could not refresh the local snapshot.", err)
	}
	outputs, err := validateAndPublish(connection.ID, staging, final, materialization, connection.SelectedObjectIDs)
	if err != nil {
		_ = os.RemoveAll(staging)
		s.recordRefreshError(ctx, id, attemptedAt, err)
		return Connection{}, apperror.Wrap("connection_refresh_failed", "The adapter returned an invalid snapshot.", err)
	}
	oldSnapshotDirs := snapshotDirectories(connection.Outputs)
	connection.SourceFingerprint = materialization.Fingerprint
	connection.Outputs = outputs
	connection.Status = StatusReady
	connection.ErrorMessage = ""
	connection.UpdatedAt = attemptedAt
	connection.LastRefreshAttemptAt = attemptedAt
	connection.LastRefreshSuccessAt = attemptedAt
	if err := s.repository.ReplaceSnapshot(ctx, connection); err != nil {
		_ = os.RemoveAll(final)
		s.recordRefreshError(ctx, id, attemptedAt, err)
		return Connection{}, apperror.Wrap("connection_refresh_failed", "Could not publish the refreshed snapshot.", err)
	}
	for directory := range oldSnapshotDirs {
		_ = os.RemoveAll(directory)
	}
	return connection, nil
}

func (s *Service) Get(ctx context.Context, connectionID string) (Connection, error) {
	connection, err := s.repository.Get(ctx, strings.TrimSpace(connectionID))
	if errors.Is(err, errNotFound) {
		return Connection{}, apperror.New("connection_not_found", "Connection not found.")
	}
	if err != nil {
		return Connection{}, apperror.Wrap("connection_load_failed", "Could not load the connection.", err)
	}
	return connection, nil
}

func (s *Service) List(ctx context.Context, workspaceID string) (ListResponse, error) {
	id := strings.TrimSpace(workspaceID)
	if id == "" {
		return ListResponse{}, apperror.New("workspace_required", "Select a workspace before loading connections.")
	}
	connections, err := s.repository.List(ctx, id)
	if err != nil {
		return ListResponse{}, apperror.Wrap("connection_list_failed", "Could not load connections.", err)
	}
	return ListResponse{Connections: connections}, nil

}

func (s *Service) Delete(ctx context.Context, connectionID string) error {
	id := strings.TrimSpace(connectionID)
	lock := s.connectionLock(id)
	lock.Lock()
	defer lock.Unlock()
	connection, err := s.Get(ctx, id)
	if err != nil {
		return err
	}
	if err := s.repository.Delete(ctx, id); errors.Is(err, errNotFound) {
		return apperror.New("connection_not_found", "Connection not found.")
	} else if err != nil {
		return apperror.Wrap("connection_delete_failed", "Could not delete the connection.", err)
	}
	_ = os.RemoveAll(filepath.Join(s.snapshotRoot, connection.WorkspaceID, connection.ID))
	return nil
}

func (s *Service) DeleteWorkspaceConnections(ctx context.Context, workspaceID string) error {
	listed, err := s.List(ctx, workspaceID)
	if err != nil {
		return err
	}
	for _, item := range listed.Connections {
		if err := s.Delete(ctx, item.ID); err != nil {
			return err
		}
	}
	return nil
}

func (s *Service) Close() error { return s.repository.Close() }

func (s *Service) recordRefreshError(ctx context.Context, id, timestamp string, cause error) {
	_ = s.repository.MarkError(ctx, id, cause.Error(), timestamp)
}

func (s *Service) connectionLock(id string) *sync.Mutex {
	value, _ := s.locks.LoadOrStore(id, &sync.Mutex{})
	return value.(*sync.Mutex)
}

func (s *Service) snapshotPaths(workspaceID, connectionID, snapshotID string) (string, string) {
	root := filepath.Join(s.snapshotRoot, workspaceID, connectionID)
	return filepath.Join(root, ".staging", snapshotID), filepath.Join(root, "snapshots", snapshotID)
}

func validateAndPublish(connectionID, staging, final string, materialization Materialization, selected []string) ([]Output, error) {
	if strings.TrimSpace(materialization.Fingerprint) == "" || len(materialization.Outputs) == 0 {
		return nil, apperror.New("adapter_invalid_output", "Adapter did not return a fingerprint and output.")
	}
	if len(materialization.Outputs) != len(selected) {
		return nil, apperror.New("adapter_invalid_output", "Adapter outputs did not match the selected source objects.")
	}
	selectedIDs := make(map[string]bool, len(selected))
	for _, id := range selected {
		selectedIDs[id] = true
	}
	seen := map[string]bool{}
	outputs := make([]Output, 0, len(materialization.Outputs))
	for _, item := range materialization.Outputs {
		objectID := strings.TrimSpace(item.SourceObjectID)
		clean := filepath.Clean(filepath.FromSlash(item.RelativePath))
		if objectID == "" || !selectedIDs[objectID] || seen[objectID] || clean == "." || filepath.IsAbs(clean) || clean == ".." || strings.HasPrefix(clean, ".."+string(filepath.Separator)) {
			return nil, apperror.New("adapter_invalid_output", "Adapter returned an unsafe or duplicate output.")
		}
		seen[objectID] = true
		stagedPath := filepath.Join(staging, clean)
		relative, err := filepath.Rel(staging, stagedPath)
		if err != nil || relative == ".." || strings.HasPrefix(relative, ".."+string(filepath.Separator)) {
			return nil, apperror.New("adapter_invalid_output", "Adapter output escaped snapshot storage.")
		}
		info, err := os.Stat(stagedPath)
		if err != nil || !info.Mode().IsRegular() || item.RowCount < 0 || item.ByteSize < 0 {
			return nil, apperror.New("adapter_invalid_output", "Adapter output file or metadata is invalid.")
		}
		outputs = append(outputs, Output{
			ID: uuid.NewString(), ConnectionID: connectionID, SourceObjectID: objectID,
			Name: strings.TrimSpace(item.Name), SnapshotPath: filepath.Join(final, clean),
			Format: strings.TrimSpace(item.Format), Columns: item.Columns,
			RowCount: item.RowCount, ByteSize: info.Size(),
		})
	}
	if err := os.MkdirAll(filepath.Dir(final), 0o700); err != nil {
		return nil, apperror.Wrap("snapshot_publish_failed", "Could not create snapshot storage.", err)
	}
	if err := os.Rename(staging, final); err != nil {
		return nil, apperror.Wrap("snapshot_publish_failed", "Could not publish the local snapshot.", err)
	}
	return outputs, nil
}

func validateName(value string) (string, string, error) {
	name := strings.TrimSpace(value)
	if name == "" {
		return "", "", apperror.New("connection_name_required", "Connection name cannot be empty.")
	}
	if len([]rune(name)) > maxConnectionNameLength {
		return "", "", apperror.New("connection_name_too_long", "Connection name must be 120 characters or fewer.")
	}
	return name, strings.ToLower(strings.Join(strings.Fields(name), " ")), nil
}

func validateSource(kind AdapterKind, value string) (string, error) {
	if !supportedAdapter(kind) {
		return "", apperror.New("adapter_not_supported", "Supported adapters are CSV, Parquet, Excel, JSON, and SQLite.")
	}
	path := strings.TrimSpace(value)
	if path == "" {
		return "", apperror.New("source_required", "Select a source file.")
	}
	absolute, err := filepath.Abs(path)
	if err != nil {
		return "", apperror.Wrap("source_invalid", "Could not resolve the source path.", err)
	}
	info, err := os.Stat(absolute)
	if errors.Is(err, os.ErrNotExist) {
		return "", apperror.New("source_not_found", "The selected source file does not exist.")
	}
	if err != nil {
		return "", apperror.Wrap("source_invalid", "Could not inspect the source file.", err)
	}
	if !info.Mode().IsRegular() {
		return "", apperror.New("source_not_file", "The selected source must be a regular file.")
	}
	if !adapterAcceptsExtension(kind, strings.ToLower(filepath.Ext(absolute))) {
		return "", apperror.New("source_extension_mismatch", fmt.Sprintf("Selected source does not match the %s adapter.", kind))
	}
	resolved, err := filepath.EvalSymlinks(absolute)
	if err != nil {
		return "", apperror.Wrap("source_invalid", "Could not resolve the source file.", err)
	}
	return resolved, nil
}

func missingSelectedObjects(objects []SourceObject, selected []string) []string {
	available := make(map[string]bool, len(objects))
	for _, object := range objects {
		available[strings.TrimSpace(object.ID)] = true
	}
	missing := make([]string, 0)
	for _, id := range selected {
		if !available[id] {
			missing = append(missing, id)
		}
	}
	return missing
}

func validateSelection(values []string) ([]string, error) {
	if len(values) == 0 {
		return nil, apperror.New("source_selection_required", "Select at least one source object.")
	}
	seen := map[string]bool{}
	result := make([]string, 0, len(values))
	for _, value := range values {
		id := strings.TrimSpace(value)
		if id == "" || seen[id] {
			return nil, apperror.New("source_selection_invalid", "Source selections must be non-empty and unique.")
		}
		seen[id] = true
		result = append(result, id)
	}
	return result, nil
}

func snapshotDirectories(outputs []Output) map[string]bool {
	result := map[string]bool{}
	for _, output := range outputs {
		if output.SnapshotPath != "" {
			result[filepath.Dir(output.SnapshotPath)] = true
		}
	}
	return result
}

func cloneOptions(options map[string]any) map[string]any {
	if options == nil {
		return map[string]any{}
	}
	result := make(map[string]any, len(options))
	for key, value := range options {
		result[key] = value
	}
	return result
}

func formatTime(value time.Time) string { return value.UTC().Format(time.RFC3339Nano) }

func isUniqueConstraint(err error) bool {
	message := strings.ToLower(err.Error())
	return strings.Contains(message, "unique constraint") || strings.Contains(message, "constraint failed")
}
