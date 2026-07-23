package main

import (
	"reflect"
	"testing"
)

func TestWailsBridgeDoesNotReintroduceRemovedCompatibilityMethods(t *testing.T) {
	appType := reflect.TypeOf(&App{})
	removedMethods := []string{
		"ApplicationPaths",
		"CreateConversationTurn",
		"CompleteConversationTurn",
		"FailConversationTurn",
		"ListTurnArtifacts",
		"ExecuteConversationCode",
		"RespondAgentIntervention",
		"MoveConversationTurn",
		"ReorderConversationTurns",
		"ListWorkspaceArtifacts",
		"GetWorkspaceArtifactMetadata",
		"GetWorkspaceArtifactUsage",
		"DeleteWorkspaceArtifact",
		"ListWorkspaceCommands",
		"ResetWorkspaceKernel",
		"InterruptWorkspaceKernel",
		"GetWorkspacePaths",
		"SelectWorkspaceDataset",
		"ListWorkspaceColumns",
		"ResetWorkspaceAIConfig",
		"RerunFinalConversationTurn",
	}
	for _, methodName := range removedMethods {
		if _, exposed := appType.MethodByName(methodName); exposed {
			t.Errorf("%s must not be exposed by the Wails bridge", methodName)
		}
	}
}
