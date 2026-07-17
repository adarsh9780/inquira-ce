package workspace

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/google/uuid"

	"inquira-go/internal/apperror"
)

type repository interface {
	List(context.Context) ([]Workspace, error)
	Get(context.Context, string) (Workspace, error)
	Create(context.Context, Workspace, string) (Workspace, error)
	Activate(context.Context, string) (Workspace, error)
	Update(context.Context, string, string, string, *string, time.Time) (Workspace, error)
	Delete(context.Context, string) error
	Close() error
}

type Service struct {
	repository repository
	now        func() time.Time
}

func NewService(repository repository) *Service {
	return &Service{repository: repository, now: time.Now}
}

func (s *Service) List(ctx context.Context) (ListResponse, error) {
	workspaces, err := s.repository.List(ctx)
	if err != nil {
		return ListResponse{}, apperror.Wrap("workspace_list_failed", "Could not load workspaces.", err)
	}
	return ListResponse{Workspaces: workspaces}, nil
}

func (s *Service) Create(ctx context.Context, request CreateRequest) (Workspace, error) {
	name, normalized, err := validateName(request.Name)
	if err != nil {
		return Workspace{}, err
	}
	now := s.now().UTC()
	created, err := s.repository.Create(ctx, Workspace{
		ID: uuid.NewString(), Name: name, SchemaContext: request.SchemaContext,
		CreatedAt: formatTime(now), UpdatedAt: formatTime(now),
	}, normalized)
	if err != nil {
		if isUniqueConstraint(err) {
			return Workspace{}, apperror.New("workspace_name_exists", "A workspace with this name already exists.")
		}
		return Workspace{}, apperror.Wrap("workspace_create_failed", "Could not create the workspace.", err)
	}
	return created, nil
}

func (s *Service) Activate(ctx context.Context, workspaceID string) (Workspace, error) {
	workspace, err := s.repository.Activate(ctx, strings.TrimSpace(workspaceID))
	if errors.Is(err, errNotFound) {
		return Workspace{}, apperror.New("workspace_not_found", "Workspace not found.")
	}
	if err != nil {
		return Workspace{}, apperror.Wrap("workspace_activate_failed", "Could not activate the workspace.", err)
	}
	return workspace, nil
}

func (s *Service) Update(ctx context.Context, request UpdateRequest) (Workspace, error) {
	name, normalized, err := validateName(request.Name)
	if err != nil {
		return Workspace{}, err
	}
	workspace, err := s.repository.Update(ctx, strings.TrimSpace(request.WorkspaceID), name, normalized,
		request.SchemaContext, s.now().UTC())
	if errors.Is(err, errNotFound) {
		return Workspace{}, apperror.New("workspace_not_found", "Workspace not found.")
	}
	if err != nil {
		if isUniqueConstraint(err) {
			return Workspace{}, apperror.New("workspace_name_exists", "A workspace with this name already exists.")
		}
		return Workspace{}, apperror.Wrap("workspace_update_failed", "Could not update the workspace.", err)
	}
	return workspace, nil
}

func (s *Service) Summary(ctx context.Context, workspaceID string) (Summary, error) {
	workspace, err := s.repository.Get(ctx, strings.TrimSpace(workspaceID))
	if errors.Is(err, errNotFound) {
		return Summary{}, apperror.New("workspace_not_found", "Workspace not found.")
	}
	if err != nil {
		return Summary{}, apperror.Wrap("workspace_summary_failed", "Could not load the workspace.", err)
	}
	return Summary{
		ID: workspace.ID, Name: workspace.Name, IsActive: workspace.IsActive,
		SchemaContext: workspace.SchemaContext, CreatedAt: workspace.CreatedAt,
		UpdatedAt: workspace.UpdatedAt, TableNames: []string{},
	}, nil
}

func (s *Service) Delete(ctx context.Context, workspaceID string) (DeletionResult, error) {
	id := strings.TrimSpace(workspaceID)
	if err := s.repository.Delete(ctx, id); errors.Is(err, errNotFound) {
		return DeletionResult{}, apperror.New("workspace_not_found", "Workspace not found.")
	} else if err != nil {
		return DeletionResult{}, apperror.Wrap("workspace_delete_failed", "Could not delete the workspace.", err)
	}
	now := s.now().UTC()
	return DeletionResult{
		JobID: uuid.NewString(), WorkspaceID: id, Status: "completed",
		CreatedAt: formatTime(now), UpdatedAt: formatTime(now),
	}, nil
}

func (s *Service) Close() error { return s.repository.Close() }

func validateName(value string) (string, string, error) {
	name := strings.TrimSpace(value)
	if name == "" {
		return "", "", apperror.New("workspace_name_required", "Workspace name cannot be empty.")
	}
	if len([]rune(name)) > maxNameLength {
		return "", "", apperror.New("workspace_name_too_long", fmt.Sprintf("Workspace name must be %d characters or fewer.", maxNameLength))
	}
	normalized := strings.ToLower(strings.Join(strings.Fields(name), " "))
	return name, normalized, nil
}

func isUniqueConstraint(err error) bool {
	message := strings.ToLower(err.Error())
	return strings.Contains(message, "unique constraint") || strings.Contains(message, "constraint failed")
}
