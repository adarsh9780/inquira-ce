package conversation

import (
	"context"
	"errors"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"testing"

	"inquira-go/internal/apperror"
	"inquira-go/internal/workspace"
)

func newTestService(t *testing.T) (*Service, string, string, string) {
	t.Helper()
	root := t.TempDir()
	databasePath := filepath.Join(root, "data", "inquira.db")
	workspaceRepository, err := workspace.OpenSQLite(databasePath)
	if err != nil {
		t.Fatal(err)
	}
	workspaceService := workspace.NewService(workspaceRepository)
	createdWorkspace, err := workspaceService.Create(context.Background(), workspace.CreateRequest{Name: "Research"})
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = workspaceService.Close() })

	repository, err := OpenSQLite(databasePath)
	if err != nil {
		t.Fatal(err)
	}
	workspaceRoot := filepath.Join(root, "data", "workspaces")
	service := NewService(repository, NewFileHeap(workspaceRoot))
	t.Cleanup(func() { _ = service.Close() })
	return service, createdWorkspace.ID, databasePath, workspaceRoot
}

func TestConversationAndTurnContentLivesOnlyInSQLite(t *testing.T) {
	service, workspaceID, databasePath, workspaceRoot := newTestService(t)
	ctx := context.Background()
	created, err := service.CreateConversation(ctx, CreateConversationRequest{WorkspaceID: workspaceID})
	if err != nil {
		t.Fatal(err)
	}
	if created.Title != DefaultTitle || created.Status != ConversationStatusActive {
		t.Fatalf("created conversation = %#v", created)
	}
	turn, err := service.CreateTurn(ctx, CreateTurnRequest{
		ConversationID: created.ID,
		UserText:       "Which region grew fastest?",
		MetadataJSON:   `{"model":"test-model"}`,
	})
	if err != nil {
		t.Fatal(err)
	}
	completed, err := service.CompleteTurn(ctx, CompleteTurnRequest{
		TurnID:         turn.ID,
		AssistantText:  "West grew fastest.",
		CodeSnapshot:   "result = sales.groupby('region').sum()",
		ToolEventsJSON: `[{"name":"python"}]`,
		ResultJSON:     `{"region":"West","growth":0.21}`,
		ResultKind:     "scalar",
	})
	if err != nil {
		t.Fatal(err)
	}
	if completed.Status != TurnStatusCompleted || completed.Sequence != 1 {
		t.Fatalf("completed turn = %#v", completed)
	}

	conversationDir := filepath.Join(workspaceRoot, workspaceID, "conversations", created.ID)
	entries, err := os.ReadDir(conversationDir)
	if err != nil {
		t.Fatal(err)
	}
	if len(entries) != 2 || entries[0].Name() != "artifacts" || entries[1].Name() != "attachments" {
		t.Fatalf("conversation heap entries = %#v", entries)
	}
	if err := filepath.WalkDir(conversationDir, func(path string, entry os.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if !entry.IsDir() {
			t.Fatalf("turn content leaked into heap: %s", path)
		}
		return nil
	}); err != nil {
		t.Fatal(err)
	}

	reopened, err := OpenSQLite(databasePath)
	if err != nil {
		t.Fatal(err)
	}
	defer reopened.Close()
	persisted, err := reopened.ListTurns(ctx, created.ID)
	if err != nil || len(persisted) != 1 {
		t.Fatalf("ListTurns() = %#v, %v", persisted, err)
	}
	if persisted[0].UserText != turn.UserText || persisted[0].AssistantText != completed.AssistantText ||
		persisted[0].CodeSnapshot != completed.CodeSnapshot || persisted[0].ResultJSON != completed.ResultJSON {
		t.Fatalf("persisted turn = %#v", persisted[0])
	}
}

func TestTurnsSupportBranchesAndAllocateUniqueSequencesConcurrently(t *testing.T) {
	service, workspaceID, _, _ := newTestService(t)
	ctx := context.Background()
	conversation, err := service.CreateConversation(ctx, CreateConversationRequest{WorkspaceID: workspaceID, Title: "Branches"})
	if err != nil {
		t.Fatal(err)
	}
	root, err := service.CreateTurn(ctx, CreateTurnRequest{ConversationID: conversation.ID, UserText: "Root"})
	if err != nil {
		t.Fatal(err)
	}
	other, err := service.CreateConversation(ctx, CreateConversationRequest{WorkspaceID: workspaceID, Title: "Other"})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := service.CreateTurn(ctx, CreateTurnRequest{ConversationID: other.ID, ParentTurnID: &root.ID, UserText: "Invalid branch"}); appErrorCode(err) != "turn_parent_not_found" {
		t.Fatalf("cross-conversation parent error = %v", err)
	}

	const count = 16
	sequences := make(chan int, count)
	errorsSeen := make(chan error, count)
	var group sync.WaitGroup
	for index := 0; index < count; index++ {
		group.Add(1)
		go func(index int) {
			defer group.Done()
			created, createErr := service.CreateTurn(ctx, CreateTurnRequest{
				ConversationID: conversation.ID,
				ParentTurnID:   &root.ID,
				UserText:       "Branch " + string(rune('A'+index)),
			})
			if createErr != nil {
				errorsSeen <- createErr
				return
			}
			sequences <- created.Sequence
		}(index)
	}
	group.Wait()
	close(sequences)
	close(errorsSeen)
	for createErr := range errorsSeen {
		t.Fatalf("CreateTurn() error = %v", createErr)
	}
	got := make([]int, 0, count)
	for sequence := range sequences {
		got = append(got, sequence)
	}
	sort.Ints(got)
	for index, sequence := range got {
		if sequence != index+2 {
			t.Fatalf("sequences = %#v", got)
		}
	}
}

func TestArtifactPayloadsAreImmutableHeapObjectsReferencedBySQLite(t *testing.T) {
	service, workspaceID, _, workspaceRoot := newTestService(t)
	ctx := context.Background()
	conversation, _ := service.CreateConversation(ctx, CreateConversationRequest{WorkspaceID: workspaceID, Title: "Artifacts"})
	turn, _ := service.CreateTurn(ctx, CreateTurnRequest{ConversationID: conversation.ID, UserText: "Make a table"})
	payload := "PAR1-test-data"
	artifact, err := service.PublishArtifact(ctx, PublishArtifactRequest{
		ConversationID: conversation.ID,
		TurnID:         turn.ID,
		Kind:           "dataframe",
		LogicalName:    "regional_sales",
		DisplayName:    "Regional sales",
		PayloadFormat:  ".PARQUET",
		MediaType:      "application/vnd.apache.parquet",
	}, strings.NewReader(payload))
	if err != nil {
		t.Fatal(err)
	}
	if filepath.IsAbs(artifact.RelativePath) || !strings.HasPrefix(filepath.ToSlash(artifact.RelativePath), "conversations/"+conversation.ID+"/artifacts/") {
		t.Fatalf("relative path = %q", artifact.RelativePath)
	}
	if artifact.PayloadFormat != "parquet" || artifact.ByteSize != int64(len(payload)) || !strings.HasPrefix(artifact.SHA256, "sha256:") {
		t.Fatalf("artifact = %#v", artifact)
	}
	absolutePath, err := service.ArtifactPath(ctx, artifact.ID)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.HasPrefix(absolutePath, filepath.Join(workspaceRoot, workspaceID)+string(os.PathSeparator)) {
		t.Fatalf("artifact escaped workspace: %q", absolutePath)
	}
	contents, err := os.ReadFile(absolutePath)
	if err != nil || string(contents) != payload {
		t.Fatalf("artifact contents = %q, %v", contents, err)
	}
	attachment, err := service.PublishArtifact(ctx, PublishArtifactRequest{
		ConversationID: conversation.ID, TurnID: turn.ID, Kind: "attachment",
		LogicalName: "source_notes", PayloadFormat: "txt", StorageClass: StorageClassAttachments,
	}, strings.NewReader("notes"))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(filepath.ToSlash(attachment.RelativePath), "/attachments/") {
		t.Fatalf("attachment path = %q", attachment.RelativePath)
	}
	listed, err := service.ListArtifacts(ctx, turn.ID)
	if err != nil || len(listed) != 2 {
		t.Fatalf("ListArtifacts() = %#v, %v", listed, err)
	}
}

func TestInvalidWritesAndReaderFailuresLeaveNoDatabaseOrHeapGarbage(t *testing.T) {
	service, workspaceID, _, workspaceRoot := newTestService(t)
	ctx := context.Background()
	conversation, _ := service.CreateConversation(ctx, CreateConversationRequest{WorkspaceID: workspaceID})
	turn, _ := service.CreateTurn(ctx, CreateTurnRequest{ConversationID: conversation.ID, UserText: "Question"})

	invalidComplete := CompleteTurnRequest{TurnID: turn.ID, AssistantText: "Answer", ResultJSON: `{broken`}
	if _, err := service.CompleteTurn(ctx, invalidComplete); appErrorCode(err) != "turn_result_invalid" {
		t.Fatalf("invalid result error = %v", err)
	}
	tests := []struct {
		name    string
		request PublishArtifactRequest
		code    string
	}{
		{"missing conversation", PublishArtifactRequest{TurnID: turn.ID, Kind: "figure", LogicalName: "chart", PayloadFormat: "json"}, "conversation_required"},
		{"unknown turn", PublishArtifactRequest{ConversationID: conversation.ID, TurnID: "missing", Kind: "figure", LogicalName: "chart", PayloadFormat: "json"}, "turn_not_found"},
		{"blank kind", PublishArtifactRequest{ConversationID: conversation.ID, TurnID: turn.ID, LogicalName: "chart", PayloadFormat: "json"}, "artifact_kind_required"},
		{"blank name", PublishArtifactRequest{ConversationID: conversation.ID, TurnID: turn.ID, Kind: "figure", PayloadFormat: "json"}, "artifact_name_required"},
		{"unsafe format", PublishArtifactRequest{ConversationID: conversation.ID, TurnID: turn.ID, Kind: "figure", LogicalName: "chart", PayloadFormat: "../json"}, "artifact_format_invalid"},
		{"unsafe class", PublishArtifactRequest{ConversationID: conversation.ID, TurnID: turn.ID, Kind: "figure", LogicalName: "chart", PayloadFormat: "json", StorageClass: "../escape"}, "artifact_storage_class_invalid"},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			if _, err := service.PublishArtifact(ctx, test.request, strings.NewReader("payload")); appErrorCode(err) != test.code {
				t.Fatalf("error = %v, want %q", err, test.code)
			}
		})
	}
	if _, err := service.PublishArtifact(ctx, PublishArtifactRequest{
		ConversationID: conversation.ID, TurnID: turn.ID, Kind: "dataframe",
		LogicalName: "broken", PayloadFormat: "parquet",
	}, failingReader{}); appErrorCode(err) != "artifact_write_failed" {
		t.Fatalf("reader failure error = %v", err)
	}
	listed, err := service.ListArtifacts(ctx, turn.ID)
	if err != nil || len(listed) != 0 {
		t.Fatalf("artifacts after failures = %#v, %v", listed, err)
	}
	conversationDir := filepath.Join(workspaceRoot, workspaceID, "conversations", conversation.ID)
	if err := filepath.WalkDir(conversationDir, func(path string, entry os.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if !entry.IsDir() {
			t.Fatalf("failed write left heap file %q", path)
		}
		return nil
	}); err != nil {
		t.Fatal(err)
	}
}

func TestReconciliationRepairsOrphansAndMissingPointers(t *testing.T) {
	service, workspaceID, _, workspaceRoot := newTestService(t)
	ctx := context.Background()
	conversation, _ := service.CreateConversation(ctx, CreateConversationRequest{WorkspaceID: workspaceID, Title: "Keep"})
	turn, _ := service.CreateTurn(ctx, CreateTurnRequest{ConversationID: conversation.ID, UserText: "Question"})
	artifact, err := service.PublishArtifact(ctx, PublishArtifactRequest{
		ConversationID: conversation.ID, TurnID: turn.ID, Kind: "figure",
		LogicalName: "chart", PayloadFormat: "json",
	}, strings.NewReader(`{"data":[]}`))
	if err != nil {
		t.Fatal(err)
	}
	artifactPath, _ := service.ArtifactPath(ctx, artifact.ID)
	if err := os.Remove(artifactPath); err != nil {
		t.Fatal(err)
	}
	orphanFile := filepath.Join(filepath.Dir(artifactPath), "orphan.json")
	if err := os.WriteFile(orphanFile, []byte("orphan"), 0o600); err != nil {
		t.Fatal(err)
	}
	orphanConversation := filepath.Join(workspaceRoot, workspaceID, "conversations", "orphan-conversation", "artifacts")
	if err := os.MkdirAll(orphanConversation, 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(orphanConversation, "payload.parquet"), []byte("orphan"), 0o600); err != nil {
		t.Fatal(err)
	}

	reconciled, err := service.ReconcileWorkspace(ctx, workspaceID)
	if err != nil {
		t.Fatal(err)
	}
	if reconciled.OrphansRemoved != 2 || reconciled.MissingArtifacts != 1 {
		t.Fatalf("reconciliation = %#v", reconciled)
	}
	if _, err := os.Stat(orphanFile); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("orphan file still exists: %v", err)
	}
	if _, err := os.Stat(filepath.Dir(orphanConversation)); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("orphan conversation still exists: %v", err)
	}
	listed, err := service.ListArtifacts(ctx, turn.ID)
	if err != nil || len(listed) != 1 || listed[0].Status != ArtifactStatusMissing {
		t.Fatalf("missing artifact state = %#v, %v", listed, err)
	}
}

func TestDeletingConversationCascadesIndexRowsAndRemovesOnlyItsHeap(t *testing.T) {
	service, workspaceID, _, workspaceRoot := newTestService(t)
	ctx := context.Background()
	first, _ := service.CreateConversation(ctx, CreateConversationRequest{WorkspaceID: workspaceID, Title: "First"})
	firstTurn, _ := service.CreateTurn(ctx, CreateTurnRequest{ConversationID: first.ID, UserText: "First question"})
	_, _ = service.PublishArtifact(ctx, PublishArtifactRequest{
		ConversationID: first.ID, TurnID: firstTurn.ID, Kind: "log", LogicalName: "execution",
		PayloadFormat: "txt",
	}, strings.NewReader("output"))
	second, _ := service.CreateConversation(ctx, CreateConversationRequest{WorkspaceID: workspaceID, Title: "Second"})

	result, err := service.DeleteConversation(ctx, first.ID)
	if err != nil || !result.Deleted {
		t.Fatalf("DeleteConversation() = %#v, %v", result, err)
	}
	if _, err := os.Stat(filepath.Join(workspaceRoot, workspaceID, "conversations", first.ID)); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("deleted heap still exists: %v", err)
	}
	if _, err := os.Stat(filepath.Join(workspaceRoot, workspaceID, "conversations", second.ID)); err != nil {
		t.Fatalf("sibling heap was removed: %v", err)
	}
	if _, err := service.ListTurns(ctx, first.ID); appErrorCode(err) != "conversation_not_found" {
		t.Fatalf("deleted conversation error = %v", err)
	}
	listed, err := service.ListConversations(ctx, workspaceID)
	if err != nil || len(listed) != 1 || listed[0].ID != second.ID {
		t.Fatalf("remaining conversations = %#v, %v", listed, err)
	}
}

type failingReader struct{}

func (failingReader) Read([]byte) (int, error) { return 0, io.ErrUnexpectedEOF }

func appErrorCode(err error) string {
	var appError *apperror.Error
	if errors.As(err, &appError) {
		return appError.Code
	}
	return ""
}
