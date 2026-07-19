package schemageneration

import (
	"context"
	"encoding/json"
	"errors"
	"strings"
	"testing"

	"inquira-go/internal/apperror"
	"inquira-go/internal/datacatalog"
	"inquira-go/internal/modelconfig"
)

type fakeCatalog struct {
	schema datacatalog.DatasetSchema
	saved  datacatalog.SaveSchemaRequest
	saves  int
	err    error
}

func (f *fakeCatalog) GetSchema(context.Context, string, string) (datacatalog.DatasetSchema, error) {
	return f.schema, f.err
}

func (f *fakeCatalog) SaveSchema(_ context.Context, request datacatalog.SaveSchemaRequest) (datacatalog.DatasetSchema, error) {
	f.saved = request
	f.saves++
	return datacatalog.DatasetSchema{TableName: request.TableName, Context: f.schema.Context, Columns: request.Columns}, f.err
}

type fakeModels struct {
	config modelconfig.RuntimeConfiguration
	calls  int
	err    error
}

func (f *fakeModels) SchemaRuntimeConfiguration(context.Context) (modelconfig.RuntimeConfiguration, error) {
	f.calls++
	return f.config, f.err
}

type fakeGateway struct {
	request GenerateRequest
	result  GenerateResult
	calls   int
	err     error
}

func (f *fakeGateway) Generate(_ context.Context, request GenerateRequest) (GenerateResult, error) {
	f.request = request
	f.calls++
	return f.result, f.err
}

func schemaErrorCode(err error) string {
	var appError *apperror.Error
	if errors.As(err, &appError) {
		return appError.Code
	}
	return ""
}

func TestRegenerateUsesLiteModelMergesByNormalizedNameAndPersistsOnce(t *testing.T) {
	catalog := &fakeCatalog{schema: datacatalog.DatasetSchema{
		TableName: "sales", Context: "Saved context", Columns: []datacatalog.SchemaColumn{
			{Name: "region", DataType: "VARCHAR", Type: "VARCHAR", Description: "Old region", Aliases: []string{"territory"}},
			{Name: "gross_margin", DataType: "DOUBLE", Type: "DOUBLE", Description: "Old margin", Aliases: []string{"margin"}},
			{Name: "booked_at", DataType: "DATE", Type: "DATE", Description: "Booking date", Aliases: []string{"date"}},
		},
	}}
	models := &fakeModels{config: modelconfig.RuntimeConfiguration{Provider: "openai", Model: "gpt-lite", APIKey: "secret"}}
	gateway := &fakeGateway{result: GenerateResult{Columns: []GeneratedColumn{
		{Name: "Gross Margin", Description: "Profit after direct costs", Aliases: []string{"profitability", "margin pct"}},
		{Name: "region", Description: "Sales territory", Aliases: []string{"area", "market", "area"}},
		{Name: "invented", Description: "Must be ignored", Aliases: []string{"bad"}},
	}}}
	service := NewService(catalog, models, gateway)

	result, err := service.Regenerate(context.Background(), RegenerateRequest{
		WorkspaceID: "workspace-1", TableName: "sales", Context: ptr("Finance reporting"),
	})
	if err != nil {
		t.Fatal(err)
	}
	if models.calls != 1 || gateway.calls != 1 || catalog.saves != 1 || gateway.request.Model.Model != "gpt-lite" {
		t.Fatalf("calls/models = %d/%d/%d request=%#v", models.calls, gateway.calls, catalog.saves, gateway.request)
	}
	if gateway.request.Context != "Finance reporting" || len(gateway.request.Columns) != 3 || gateway.request.Columns[1].Name != "gross_margin" {
		t.Fatalf("generation request = %#v", gateway.request)
	}
	if result.Columns[0].Description != "Sales territory" || len(result.Columns[0].Aliases) != 2 {
		t.Fatalf("exact generated column = %#v", result.Columns[0])
	}
	if result.Columns[1].Description != "Profit after direct costs" || result.Columns[1].DataType != "DOUBLE" {
		t.Fatalf("normalized generated column = %#v", result.Columns[1])
	}
	if result.Columns[2].Description != "Booking date" || result.Columns[2].Aliases[0] != "date" {
		t.Fatalf("omitted column metadata was not preserved: %#v", result.Columns[2])
	}
	persisted, _ := json.Marshal(catalog.saved)
	if strings.Contains(string(persisted), "secret") || strings.Contains(string(persisted), "gpt-lite") {
		t.Fatalf("runtime model configuration leaked into persisted schema: %s", persisted)
	}
}

func TestRegenerateValidatesBeforeCallingModelAndDoesNotPersistPartialFailure(t *testing.T) {
	for _, request := range []RegenerateRequest{
		{},
		{WorkspaceID: "workspace", TableName: ""},
		{WorkspaceID: "workspace", TableName: "table", Context: ptr(string(make([]byte, 8001)))},
	} {
		catalog, models, gateway := &fakeCatalog{}, &fakeModels{}, &fakeGateway{}
		_, err := NewService(catalog, models, gateway).Regenerate(context.Background(), request)
		if err == nil || models.calls != 0 || gateway.calls != 0 || catalog.saves != 0 {
			t.Fatalf("invalid request %#v: err=%v calls=%d/%d/%d", request, err, models.calls, gateway.calls, catalog.saves)
		}
	}
	catalog := &fakeCatalog{schema: datacatalog.DatasetSchema{TableName: "sales", Columns: []datacatalog.SchemaColumn{{Name: "amount", DataType: "DOUBLE"}}}}
	gateway := &fakeGateway{err: errors.New("provider failed")}
	_, err := NewService(catalog, &fakeModels{config: modelconfig.RuntimeConfiguration{Model: "lite"}}, gateway).Regenerate(context.Background(), RegenerateRequest{WorkspaceID: "workspace", TableName: "sales"})
	if schemaErrorCode(err) != "schema_generation_failed" || catalog.saves != 0 {
		t.Fatalf("generation failure = %v, saves=%d", err, catalog.saves)
	}
}

func ptr(value string) *string { return &value }
