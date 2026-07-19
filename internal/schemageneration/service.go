package schemageneration

import (
	"context"
	"strings"
	"sync"
	"unicode"
	"unicode/utf8"

	"inquira-go/internal/apperror"
	"inquira-go/internal/datacatalog"
	"inquira-go/internal/modelconfig"
)

const maxContextRunes = 8000

type catalogStore interface {
	GetSchema(context.Context, string, string) (datacatalog.DatasetSchema, error)
	SaveSchema(context.Context, datacatalog.SaveSchemaRequest) (datacatalog.DatasetSchema, error)
}

type modelSource interface {
	SchemaRuntimeConfiguration(context.Context) (modelconfig.RuntimeConfiguration, error)
}

type Gateway interface {
	Generate(context.Context, GenerateRequest) (GenerateResult, error)
}

type Service struct {
	catalog catalogStore
	models  modelSource
	gateway Gateway
	locks   sync.Map
}

func NewService(catalog catalogStore, models modelSource, gateway Gateway) *Service {
	return &Service{catalog: catalog, models: models, gateway: gateway}
}

func (s *Service) Regenerate(ctx context.Context, request RegenerateRequest) (RegenerateResult, error) {
	workspaceID := strings.TrimSpace(request.WorkspaceID)
	tableName := strings.TrimSpace(request.TableName)
	if workspaceID == "" {
		return RegenerateResult{}, apperror.New("workspace_required", "Choose a workspace before regenerating schema descriptions.")
	}
	if tableName == "" {
		return RegenerateResult{}, apperror.New("dataset_required", "Choose a dataset before regenerating schema descriptions.")
	}
	if request.Context != nil && utf8.RuneCountInString(*request.Context) > maxContextRunes {
		return RegenerateResult{}, apperror.New("schema_context_invalid", "Schema context must be at most 8000 characters.")
	}

	lock := s.regenerationLock(workspaceID + "\x00" + tableName)
	lock.Lock()
	defer lock.Unlock()

	current, err := s.catalog.GetSchema(ctx, workspaceID, tableName)
	if err != nil {
		return RegenerateResult{}, err
	}
	if len(current.Columns) == 0 {
		return RegenerateResult{}, apperror.New("schema_columns_empty", "This dataset has no columns to describe.")
	}
	contextValue := current.Context
	if request.Context != nil {
		contextValue = strings.TrimSpace(*request.Context)
	}
	model, err := s.models.SchemaRuntimeConfiguration(ctx)
	if err != nil {
		return RegenerateResult{}, err
	}
	workerRequest := GenerateRequest{
		WorkspaceID: workspaceID, TableName: current.TableName, Context: contextValue,
		Columns: make([]InputColumn, 0, len(current.Columns)), Model: model,
	}
	for _, column := range current.Columns {
		workerRequest.Columns = append(workerRequest.Columns, InputColumn{
			Name: column.Name, DataType: column.DataType, Nullable: column.Nullable,
		})
	}
	generated, err := s.gateway.Generate(ctx, workerRequest)
	if err != nil {
		return RegenerateResult{}, apperror.Wrap("schema_generation_failed", "The model could not generate schema descriptions.", err)
	}
	merged, matched, err := mergeGeneratedColumns(current.Columns, generated.Columns)
	if err != nil {
		return RegenerateResult{}, err
	}
	if matched == 0 {
		return RegenerateResult{}, apperror.New("schema_generation_empty", "The model did not return descriptions for any dataset columns.")
	}
	return s.catalog.SaveSchema(ctx, datacatalog.SaveSchemaRequest{
		WorkspaceID: workspaceID, TableName: current.TableName, Columns: merged,
	})
}

func (s *Service) regenerationLock(key string) *sync.Mutex {
	value, _ := s.locks.LoadOrStore(key, &sync.Mutex{})
	return value.(*sync.Mutex)
}

func mergeGeneratedColumns(physical []datacatalog.SchemaColumn, generated []GeneratedColumn) ([]datacatalog.SchemaColumn, int, error) {
	exact := make(map[string]GeneratedColumn, len(generated))
	normalized := make(map[string]GeneratedColumn, len(generated))
	ambiguousGenerated := map[string]bool{}
	for _, item := range generated {
		item.Name = strings.TrimSpace(item.Name)
		item.Description = strings.TrimSpace(item.Description)
		if item.Name == "" || (item.Description == "" && len(item.Aliases) == 0) {
			continue
		}
		if utf8.RuneCountInString(item.Description) > 4000 {
			return nil, 0, apperror.New("schema_generation_invalid", "The model returned an invalid column description.")
		}
		aliases, err := generatedAliases(item.Aliases)
		if err != nil {
			return nil, 0, err
		}
		item.Aliases = aliases
		if _, exists := exact[item.Name]; !exists {
			exact[item.Name] = item
		}
		key := normalizedColumnName(item.Name)
		if key == "" {
			continue
		}
		if _, exists := normalized[key]; exists {
			ambiguousGenerated[key] = true
		} else {
			normalized[key] = item
		}
	}
	physicalNormalizedCounts := map[string]int{}
	for _, column := range physical {
		physicalNormalizedCounts[normalizedColumnName(column.Name)]++
	}
	result := make([]datacatalog.SchemaColumn, 0, len(physical))
	matched := 0
	for _, column := range physical {
		item, found := exact[column.Name]
		if !found {
			key := normalizedColumnName(column.Name)
			if physicalNormalizedCounts[key] == 1 && !ambiguousGenerated[key] {
				item, found = normalized[key]
			}
		}
		if found {
			matched++
			if item.Description != "" {
				column.Description = item.Description
			}
			if len(item.Aliases) > 0 {
				column.Aliases = item.Aliases
			}
		}
		result = append(result, column)
	}
	return result, matched, nil
}

func generatedAliases(values []string) ([]string, error) {
	result := make([]string, 0, 5)
	seen := map[string]bool{}
	for _, value := range values {
		alias := strings.TrimSpace(value)
		if alias == "" {
			continue
		}
		if utf8.RuneCountInString(alias) > 255 {
			return nil, apperror.New("schema_generation_invalid", "The model returned an invalid column alias.")
		}
		key := strings.ToLower(alias)
		if !seen[key] {
			seen[key] = true
			result = append(result, alias)
			if len(result) == 5 {
				break
			}
		}
	}
	return result, nil
}

func normalizedColumnName(value string) string {
	var result strings.Builder
	for _, current := range strings.TrimSpace(value) {
		if unicode.IsLetter(current) || unicode.IsDigit(current) {
			result.WriteRune(unicode.ToLower(current))
		}
	}
	return result.String()
}
