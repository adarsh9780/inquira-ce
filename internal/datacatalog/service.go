package datacatalog

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"unicode"

	"inquira-go/internal/apperror"
	"inquira-go/internal/connection"
	"inquira-go/internal/workspace"
)

type workspaceSource interface {
	Summary(context.Context, string) (workspace.Summary, error)
}

type connectionSource interface {
	List(context.Context, string) (connection.ListResponse, error)
}

type Gateway interface {
	Build(context.Context, BuildRequest) (BuildResult, error)
}

type Service struct {
	workspaces  workspaceSource
	connections connectionSource
	gateway     Gateway
	root        string
	locks       sync.Map
}

func NewService(workspaces workspaceSource, connections connectionSource, gateway Gateway, root string) *Service {
	return &Service{workspaces: workspaces, connections: connections, gateway: gateway, root: root}
}

func (s *Service) Prepare(ctx context.Context, workspaceID string) (Catalog, error) {
	id := strings.TrimSpace(workspaceID)
	lock := s.workspaceLock(id)
	lock.Lock()
	defer lock.Unlock()

	summary, err := s.workspaces.Summary(ctx, id)
	if err != nil {
		return Catalog{}, apperror.Wrap("catalog_workspace_failed", "Could not load the workspace for analysis.", err)
	}
	if !safePathComponent(summary.ID) || summary.ID != id {
		return Catalog{}, apperror.New("catalog_workspace_invalid", "Workspace storage identity is invalid.")
	}
	listed, err := s.connections.List(ctx, id)
	if err != nil {
		return Catalog{}, apperror.Wrap("catalog_connections_failed", "Could not load workspace connections.", err)
	}
	tables, err := buildTables(listed.Connections)
	if err != nil {
		return Catalog{}, err
	}
	fingerprint, err := catalogFingerprint(tables)
	if err != nil {
		return Catalog{}, apperror.Wrap("catalog_fingerprint_failed", "Could not identify the workspace data catalog.", err)
	}
	databasePath := filepath.Join(s.root, id, "workspace.duckdb")
	request := BuildRequest{DatabasePath: databasePath, Fingerprint: fingerprint, Tables: make([]BuildTable, 0, len(tables))}
	for _, table := range tables {
		request.Tables = append(request.Tables, BuildTable{ID: table.ID, Name: table.Name, SnapshotPath: table.SnapshotPath})
	}
	result, err := s.gateway.Build(ctx, request)
	if err != nil {
		return Catalog{}, apperror.Wrap("catalog_build_failed", "Could not prepare workspace data for analysis.", err)
	}
	if filepath.Clean(result.DatabasePath) != filepath.Clean(databasePath) ||
		result.Fingerprint != fingerprint || result.TableCount != len(tables) || result.ByteSize < 0 {
		return Catalog{}, apperror.New("catalog_invalid_result", "The data worker returned an invalid workspace catalog.")
	}
	return Catalog{
		WorkspaceID: id, DatabasePath: databasePath, Fingerprint: fingerprint,
		Tables: tables, Changed: result.Changed, ByteSize: result.ByteSize,
	}, nil
}

func (s *Service) Remove(workspaceID string) error {
	id := strings.TrimSpace(workspaceID)
	if !safePathComponent(id) {
		return apperror.New("catalog_workspace_invalid", "Workspace storage identity is invalid.")
	}
	if err := os.RemoveAll(filepath.Join(s.root, id)); err != nil {
		return apperror.Wrap("catalog_delete_failed", "Could not remove the workspace analysis catalog.", err)
	}
	return nil
}

func (s *Service) workspaceLock(id string) *sync.Mutex {
	value, _ := s.locks.LoadOrStore(id, &sync.Mutex{})
	return value.(*sync.Mutex)
}

func buildTables(connections []connection.Connection) ([]Table, error) {
	ordered := append([]connection.Connection(nil), connections...)
	sort.Slice(ordered, func(i, j int) bool { return ordered[i].ID < ordered[j].ID })
	tables := make([]Table, 0)
	usedNames := map[string]bool{}
	for _, item := range ordered {
		item.Outputs = append([]connection.Output(nil), item.Outputs...)
		sort.Slice(item.Outputs, func(i, j int) bool {
			return item.Outputs[i].SourceObjectID < item.Outputs[j].SourceObjectID
		})
		multiple := len(item.Outputs) > 1
		for _, output := range item.Outputs {
			info, err := os.Stat(output.SnapshotPath)
			if err != nil || !info.Mode().IsRegular() || info.Size() == 0 || strings.ToLower(filepath.Ext(output.SnapshotPath)) != ".parquet" {
				return nil, apperror.New("catalog_snapshot_missing", "A connection snapshot required for analysis is missing or invalid.")
			}
			base := item.Name
			if multiple {
				base += "_" + output.Name
			}
			stableKey := item.ID + "\x00" + output.SourceObjectID
			name := uniqueName(normalizeName(base), stableKey, usedNames)
			status := TableStatusReady
			if item.Status != connection.StatusReady {
				status = TableStatusStale
			}
			tables = append(tables, Table{
				ID: stableID(stableKey), ConnectionID: item.ID, SourceObjectID: output.SourceObjectID,
				Name: name, SnapshotPath: output.SnapshotPath, Columns: output.Columns,
				RowCount: output.RowCount, Status: status,
			})
		}
	}
	return tables, nil
}

func normalizeName(value string) string {
	var result strings.Builder
	separator := false
	for _, current := range strings.TrimSpace(value) {
		if unicode.IsLetter(current) || unicode.IsDigit(current) {
			if separator && result.Len() > 0 {
				result.WriteByte('_')
			}
			result.WriteRune(unicode.ToLower(current))
			separator = false
		} else {
			separator = true
		}
	}
	name := strings.Trim(result.String(), "_")
	if name == "" {
		name = "table"
	}
	if unicode.IsDigit([]rune(name)[0]) {
		name = "_" + name
	}
	return name
}

func uniqueName(base, stableKey string, used map[string]bool) string {
	key := strings.ToLower(base)
	if !used[key] {
		used[key] = true
		return base
	}
	suffix := shortHash(stableKey)
	name := base + "_" + suffix
	for index := 2; used[strings.ToLower(name)]; index++ {
		name = fmt.Sprintf("%s_%s_%d", base, suffix, index)
	}
	used[strings.ToLower(name)] = true
	return name
}

func stableID(value string) string { return "table_" + shortHash(value+"\x00id") }

func shortHash(value string) string {
	digest := sha256.Sum256([]byte(value))
	return hex.EncodeToString(digest[:])[:12]
}

func catalogFingerprint(tables []Table) (string, error) {
	encoded, err := json.Marshal(tables)
	if err != nil {
		return "", err
	}
	digest := sha256.Sum256(encoded)
	return "sha256:" + hex.EncodeToString(digest[:]), nil
}

func safePathComponent(value string) bool {
	return value != "" && value != "." && value != ".." && filepath.Base(value) == value
}
