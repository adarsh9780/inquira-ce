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

	"github.com/adarsh9780/inquira-ce/internal/apperror"
	"github.com/adarsh9780/inquira-ce/internal/connection"
	"github.com/adarsh9780/inquira-ce/internal/workspace"
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

type schemaRepository interface {
	List(context.Context, string, string) ([]ColumnOverride, error)
	Replace(context.Context, string, string, []ColumnOverride) error
	Close() error
}

type emptySchemaRepository struct{}

func (emptySchemaRepository) List(context.Context, string, string) ([]ColumnOverride, error) {
	return nil, nil
}
func (emptySchemaRepository) Replace(context.Context, string, string, []ColumnOverride) error {
	return nil
}
func (emptySchemaRepository) Close() error { return nil }

type Service struct {
	workspaces  workspaceSource
	connections connectionSource
	gateway     Gateway
	schemas     schemaRepository
	root        string
	locks       sync.Map
}

func NewService(workspaces workspaceSource, connections connectionSource, gateway Gateway, root string) *Service {
	return &Service{workspaces: workspaces, connections: connections, gateway: gateway, schemas: emptySchemaRepository{}, root: root}
}

func (s *Service) WithSchemaRepository(repository schemaRepository) *Service {
	if repository != nil {
		s.schemas = repository
	}
	return s
}

func (s *Service) Close() error { return s.schemas.Close() }

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
	if !sameCatalogPath(result.DatabasePath, databasePath) ||
		result.Fingerprint != fingerprint || result.TableCount != len(tables) || result.ByteSize < 0 {
		return Catalog{}, apperror.New("catalog_invalid_result", "The data worker returned an invalid workspace catalog.")
	}
	analysisSchema, err := s.buildAnalysisSchema(ctx, summary, tables)
	if err != nil {
		return Catalog{}, err
	}
	return Catalog{
		WorkspaceID: id, DatabasePath: databasePath, Fingerprint: fingerprint,
		Tables: tables, AnalysisSchema: analysisSchema, Changed: result.Changed, ByteSize: result.ByteSize,
	}, nil
}

func sameCatalogPath(left, right string) bool {
	leftAbsolute, leftErr := filepath.Abs(filepath.Clean(left))
	rightAbsolute, rightErr := filepath.Abs(filepath.Clean(right))
	if leftErr != nil || rightErr != nil {
		return false
	}
	leftResolved, leftErr := filepath.EvalSymlinks(leftAbsolute)
	rightResolved, rightErr := filepath.EvalSymlinks(rightAbsolute)
	if leftErr == nil && rightErr == nil {
		return leftResolved == rightResolved
	}
	return leftAbsolute == rightAbsolute
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

func (s *Service) ListDatasets(ctx context.Context, workspaceID string) (DatasetListResponse, error) {
	catalog, err := s.Prepare(ctx, workspaceID)
	if err != nil {
		return DatasetListResponse{}, err
	}
	result := DatasetListResponse{Datasets: make([]Dataset, 0, len(catalog.Tables))}
	for _, table := range catalog.Tables {
		result.Datasets = append(result.Datasets, Dataset{
			ID: table.ID, WorkspaceID: catalog.WorkspaceID, ConnectionID: table.ConnectionID,
			SourceObjectID: table.SourceObjectID, SourcePath: table.SourcePath, TableName: table.Name,
			RowCount: table.RowCount, FileType: table.FileType, SchemaStatus: string(table.Status),
			CreatedAt: table.CreatedAt, UpdatedAt: table.UpdatedAt,
		})
	}
	return result, nil
}

func (s *Service) SummarizeWorkspace(ctx context.Context, workspaceID string) (workspace.Summary, error) {
	id := strings.TrimSpace(workspaceID)
	summary, err := s.workspaces.Summary(ctx, id)
	if err != nil {
		return workspace.Summary{}, err
	}
	listed, err := s.connections.List(ctx, id)
	if err != nil {
		return workspace.Summary{}, apperror.Wrap("catalog_connections_failed", "Could not load workspace connections.", err)
	}
	tables, err := buildTables(listed.Connections)
	if err != nil {
		return workspace.Summary{}, err
	}
	summary.TableCount = len(tables)
	summary.TableNames = make([]string, 0, len(tables))
	for _, table := range tables {
		summary.TableNames = append(summary.TableNames, table.Name)
	}
	return summary, nil
}

func (s *Service) GetSchema(ctx context.Context, workspaceID, tableName string) (DatasetSchema, error) {
	catalog, err := s.Prepare(ctx, workspaceID)
	if err != nil {
		return DatasetSchema{}, err
	}
	table, ok := findTable(catalog.Tables, tableName)
	if !ok {
		return DatasetSchema{}, apperror.New("dataset_not_found", "Dataset not found in this workspace.")
	}
	overrides, err := s.schemas.List(ctx, catalog.WorkspaceID, table.Name)
	if err != nil {
		return DatasetSchema{}, apperror.Wrap("schema_read_failed", "Could not load dataset descriptions.", err)
	}
	byName := make(map[string]ColumnOverride, len(overrides))
	for _, item := range overrides {
		byName[item.Name] = item
	}
	summary, err := s.workspaces.Summary(ctx, catalog.WorkspaceID)
	if err != nil {
		return DatasetSchema{}, apperror.Wrap("schema_workspace_failed", "Could not load the workspace schema context.", err)
	}
	result := DatasetSchema{TableName: table.Name, Context: summary.SchemaContext, Columns: make([]SchemaColumn, 0, len(table.Columns))}
	for _, column := range table.Columns {
		override := byName[column.Name]
		result.Columns = append(result.Columns, SchemaColumn{
			Name: column.Name, DataType: column.DataType, Type: column.DataType, Nullable: column.Nullable,
			Description: override.Description, Aliases: append([]string(nil), override.Aliases...),
		})
	}
	return result, nil
}

func (s *Service) SaveSchema(ctx context.Context, request SaveSchemaRequest) (DatasetSchema, error) {
	current, err := s.GetSchema(ctx, strings.TrimSpace(request.WorkspaceID), strings.TrimSpace(request.TableName))
	if err != nil {
		return DatasetSchema{}, err
	}
	if len(request.Columns) != len(current.Columns) {
		return DatasetSchema{}, apperror.New("schema_columns_invalid", "Schema must include every physical column exactly once.")
	}
	physical := make(map[string]bool, len(current.Columns))
	for _, column := range current.Columns {
		physical[column.Name] = true
	}
	seen := make(map[string]bool, len(request.Columns))
	overrides := make([]ColumnOverride, 0, len(request.Columns))
	for _, column := range request.Columns {
		name := strings.TrimSpace(column.Name)
		if name == "" || !physical[name] || seen[name] {
			return DatasetSchema{}, apperror.New("schema_columns_invalid", "Schema must include every physical column exactly once.")
		}
		seen[name] = true
		description := strings.TrimSpace(column.Description)
		if len(description) > 4000 {
			return DatasetSchema{}, apperror.New("schema_description_invalid", "Column descriptions must be at most 4000 characters.")
		}
		aliases, err := normalizeAliases(column.Aliases)
		if err != nil {
			return DatasetSchema{}, err
		}
		overrides = append(overrides, ColumnOverride{Name: name, Description: description, Aliases: aliases})
	}
	if err := s.schemas.Replace(ctx, strings.TrimSpace(request.WorkspaceID), current.TableName, overrides); err != nil {
		return DatasetSchema{}, apperror.Wrap("schema_save_failed", "Could not save dataset descriptions.", err)
	}
	return s.GetSchema(ctx, request.WorkspaceID, current.TableName)
}

func (s *Service) workspaceLock(id string) *sync.Mutex {
	value, _ := s.locks.LoadOrStore(id, &sync.Mutex{})
	return value.(*sync.Mutex)
}

func (s *Service) buildAnalysisSchema(ctx context.Context, summary workspace.Summary, tables []Table) (AnalysisSchema, error) {
	result := AnalysisSchema{Context: summary.SchemaContext, Tables: make([]AnalysisTable, 0, len(tables))}
	for _, table := range tables {
		overrides, err := s.schemas.List(ctx, summary.ID, table.Name)
		if err != nil {
			return AnalysisSchema{}, apperror.Wrap("schema_read_failed", "Could not load dataset descriptions.", err)
		}
		byName := make(map[string]ColumnOverride, len(overrides))
		for _, item := range overrides {
			byName[item.Name] = item
		}
		analysisTable := AnalysisTable{Name: table.Name, Columns: make([]SchemaColumn, 0, len(table.Columns))}
		for _, column := range table.Columns {
			override := byName[column.Name]
			analysisTable.Columns = append(analysisTable.Columns, SchemaColumn{
				Name: column.Name, DataType: column.DataType, Type: column.DataType, Nullable: column.Nullable,
				Description: override.Description, Aliases: append([]string(nil), override.Aliases...),
			})
		}
		result.Tables = append(result.Tables, analysisTable)
	}
	return result, nil
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
				Name: name, SourcePath: item.SourcePath, FileType: string(item.AdapterKind),
				SnapshotPath: output.SnapshotPath, Columns: output.Columns, RowCount: output.RowCount,
				Status: status, CreatedAt: item.CreatedAt, UpdatedAt: item.UpdatedAt,
			})
		}
	}
	return tables, nil
}

func findTable(tables []Table, tableName string) (Table, bool) {
	wanted := strings.TrimSpace(tableName)
	for _, table := range tables {
		if table.Name == wanted {
			return table, true
		}
	}
	return Table{}, false
}

func normalizeAliases(values []string) ([]string, error) {
	result := make([]string, 0, len(values))
	seen := map[string]bool{}
	for _, value := range values {
		alias := strings.TrimSpace(value)
		if alias == "" {
			continue
		}
		if len(alias) > 255 {
			return nil, apperror.New("schema_alias_invalid", "Column aliases must be at most 255 characters.")
		}
		key := strings.ToLower(alias)
		if !seen[key] {
			seen[key] = true
			result = append(result, alias)
		}
	}
	if len(result) > 100 {
		return nil, apperror.New("schema_alias_invalid", "A column can have at most 100 aliases.")
	}
	return result, nil
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
	type fingerprintTable struct {
		Table
		SnapshotPath string `json:"snapshot_path"`
	}
	values := make([]fingerprintTable, 0, len(tables))
	for _, table := range tables {
		values = append(values, fingerprintTable{Table: table, SnapshotPath: table.SnapshotPath})
	}
	encoded, err := json.Marshal(values)
	if err != nil {
		return "", err
	}
	digest := sha256.Sum256(encoded)
	return "sha256:" + hex.EncodeToString(digest[:]), nil
}

func safePathComponent(value string) bool {
	return value != "" && value != "." && value != ".." && filepath.Base(value) == value
}
