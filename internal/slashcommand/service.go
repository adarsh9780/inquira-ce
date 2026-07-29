package slashcommand

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"

	"github.com/adarsh9780/inquira-ce/internal/analysisruntime"
	"github.com/adarsh9780/inquira-ce/internal/apperror"
	"github.com/adarsh9780/inquira-ce/internal/conversation"
	"github.com/adarsh9780/inquira-ce/internal/datacatalog"
)

type conversationStore interface {
	CreateConversation(context.Context, conversation.CreateConversationRequest) (conversation.Conversation, error)
	GetConversation(context.Context, string) (conversation.Conversation, error)
	CreateTurn(context.Context, conversation.CreateTurnRequest) (conversation.Turn, error)
	FailTurn(context.Context, conversation.FailTurnRequest) (conversation.Turn, error)
	MarkFinalTurn(context.Context, string, string) (conversation.Turn, error)
}

type catalogSource interface {
	Prepare(context.Context, string) (datacatalog.Catalog, error)
}

type compiler interface {
	Compile(context.Context, CompileRequest) (CompiledCommand, error)
}

type executor interface {
	Execute(context.Context, analysisruntime.ExecuteRequest, func(analysisruntime.WorkerEvent)) (analysisruntime.ExecuteResult, error)
}

type Service struct {
	conversations conversationStore
	catalog       catalogSource
	compiler      compiler
	executor      executor
}

func NewService(conversations conversationStore, catalog catalogSource, compiler compiler, executor executor) *Service {
	return &Service{conversations: conversations, catalog: catalog, compiler: compiler, executor: executor}
}

func (s *Service) Execute(ctx context.Context, request ExecuteRequest, emit func(analysisruntime.WorkerEvent)) (ExecuteResult, error) {
	workspaceID := strings.TrimSpace(request.WorkspaceID)
	commandText := normalizedCommandText(request)
	if workspaceID == "" {
		return ExecuteResult{}, apperror.New("workspace_required", "Choose a workspace before running a command.")
	}
	if commandText == "" {
		return ExecuteResult{}, apperror.New("command_required", "Command text is required.")
	}
	rowLimit := request.RowLimit
	if rowLimit == 0 {
		rowLimit = defaultRowLimit
	}
	if rowLimit < 1 || rowLimit > maxRowLimit {
		return ExecuteResult{}, apperror.New("command_row_limit_invalid", "Command row limit must be between 1 and 2000.")
	}

	prepared, err := s.catalog.Prepare(ctx, workspaceID)
	if err != nil {
		return ExecuteResult{}, err
	}
	owned, err := s.resolveConversation(ctx, workspaceID, request.ConversationID, commandText)
	if err != nil {
		return ExecuteResult{}, err
	}
	metadata := commandMetadata(strings.TrimPrefix(strings.Fields(commandText)[0], "/"), "message", false)
	turn, err := s.conversations.CreateTurn(ctx, conversation.CreateTurnRequest{
		ConversationID: owned.ID, ParentTurnID: owned.FinalTurnID,
		UserText: commandText, MetadataJSON: metadata,
	})
	if err != nil {
		return ExecuteResult{}, err
	}

	compiled, err := s.compiler.Compile(ctx, CompileRequest{
		Text: commandText, Name: request.Name, RawArgs: request.RawArgs,
		DefaultTable: strings.TrimSpace(request.DefaultTable), RowLimit: rowLimit,
		Columns: catalogColumns(prepared),
	})
	if err != nil {
		message := strings.TrimSpace(err.Error())
		if message == "" {
			message = "The command could not be compiled."
		}
		_, _ = s.conversations.FailTurn(context.WithoutCancel(ctx), conversation.FailTurnRequest{
			TurnID: turn.ID, AssistantText: "Command failed: " + message,
			ErrorMessage: message, MetadataJSON: commandMetadata(strings.TrimPrefix(strings.Fields(commandText)[0], "/"), "error", false),
		})
		return ExecuteResult{}, apperror.Wrap("command_invalid", message, err)
	}
	if strings.TrimSpace(compiled.PythonCode) == "" || strings.TrimSpace(compiled.Name) == "" {
		return ExecuteResult{}, apperror.New("command_compile_failed", "The command compiler returned an invalid execution plan.")
	}
	assistantText := strings.TrimSpace(compiled.Output)
	if assistantText == "" {
		assistantText = fmt.Sprintf("Executed /%s.", compiled.Name)
	}
	metadata = commandMetadata(compiled.Name, compiled.ResultType, compiled.Truncated)
	execution, err := s.executor.Execute(ctx, analysisruntime.ExecuteRequest{
		ConversationID: owned.ID, TurnID: turn.ID, Code: compiled.PythonCode,
		TimeoutSeconds: 60, AssistantText: assistantText, MetadataJSON: metadata, UseResultOutput: true,
	}, emit)
	if err != nil {
		return ExecuteResult{}, err
	}
	if !execution.Success {
		message := strings.TrimSpace(execution.Error)
		if message == "" {
			message = "Command execution failed."
		}
		return ExecuteResult{}, apperror.New("command_execution_failed", message)
	}

	result, err := decodeWorkerResult(execution.Result)
	if err != nil {
		return ExecuteResult{}, apperror.Wrap("command_result_invalid", "Command execution returned an invalid result.", err)
	}
	if _, err := s.conversations.MarkFinalTurn(ctx, owned.ID, turn.ID); err != nil {
		return ExecuteResult{}, err
	}
	return ExecuteResult{
		Command: commandText, Name: firstNonEmpty(result.Name, compiled.Name),
		Output:     firstNonEmpty(result.Output, compiled.Output, assistantText),
		ResultType: firstNonEmpty(result.ResultType, compiled.ResultType, "message"),
		Result:     result.Result, Truncated: result.Truncated,
		ConversationID: owned.ID, TurnID: turn.ID,
	}, nil
}

func (s *Service) resolveConversation(ctx context.Context, workspaceID, conversationID, commandText string) (conversation.Conversation, error) {
	id := strings.TrimSpace(conversationID)
	if id == "" {
		return s.conversations.CreateConversation(ctx, conversation.CreateConversationRequest{
			WorkspaceID: workspaceID, Title: commandTitle(commandText),
		})
	}
	owned, err := s.conversations.GetConversation(ctx, id)
	if err != nil {
		return conversation.Conversation{}, err
	}
	if owned.WorkspaceID != workspaceID {
		return conversation.Conversation{}, apperror.New("conversation_workspace_mismatch", "Conversation does not belong to this workspace.")
	}
	return owned, nil
}

func normalizedCommandText(request ExecuteRequest) string {
	if text := strings.TrimSpace(request.Text); text != "" {
		return text
	}
	name := strings.TrimPrefix(strings.TrimSpace(request.Name), "/")
	if name == "" {
		return ""
	}
	if args := strings.TrimSpace(request.RawArgs); args != "" {
		return "/" + name + " " + args
	}
	return "/" + name
}

func commandTitle(command string) string {
	compact := strings.Join(strings.Fields(command), " ")
	if len(compact) <= 80 {
		return compact
	}
	return strings.TrimSpace(compact[:77]) + "..."
}

func catalogColumns(catalog datacatalog.Catalog) []datacatalog.WorkspaceColumn {
	columns := make([]datacatalog.WorkspaceColumn, 0)
	for _, table := range catalog.Tables {
		for _, column := range table.Columns {
			columns = append(columns, datacatalog.WorkspaceColumn{
				TableName: table.Name, ColumnName: column.Name, DataType: column.DataType,
			})
		}
	}
	return columns
}

func commandMetadata(name, resultType string, truncated bool) string {
	value, _ := json.Marshal(map[string]any{
		"source": "slash_command", "execution_source": "slash_command",
		"command_name": name, "result_type": resultType, "truncated": truncated,
	})
	return string(value)
}

type workerCommandResult struct {
	Name       string          `json:"name"`
	Output     string          `json:"output"`
	ResultType string          `json:"result_type"`
	Result     json.RawMessage `json:"result"`
	Truncated  bool            `json:"truncated"`
}

func decodeWorkerResult(raw json.RawMessage) (workerCommandResult, error) {
	var result workerCommandResult
	if len(raw) == 0 || string(raw) == "null" {
		return result, fmt.Errorf("empty command result")
	}
	if err := json.Unmarshal(raw, &result); err != nil {
		return result, err
	}
	if strings.TrimSpace(result.Name) == "" {
		return result, fmt.Errorf("command name is missing")
	}
	if len(result.Result) == 0 {
		result.Result = json.RawMessage("null")
	}
	return result, nil
}

func firstNonEmpty(values ...string) string {
	for _, value := range values {
		if trimmed := strings.TrimSpace(value); trimmed != "" {
			return trimmed
		}
	}
	return ""
}
