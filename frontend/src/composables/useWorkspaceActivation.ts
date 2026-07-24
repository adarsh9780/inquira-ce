import { computed, proxyRefs } from 'vue'
import { useArtifactStore } from '../stores/artifactStore'
import { useConversationStore } from '../stores/conversationStore'
import { useExecutionStore } from '../stores/executionStore'
import { usePreferencesStore } from '../stores/preferencesStore'
import { useUiStore } from '../stores/uiStore'
import { useWorkspaceStore } from '../stores/workspaceStore'

export function useWorkspaceActivation() {
  const ui = useUiStore()
  const preferences = usePreferencesStore()
  const artifacts = useArtifactStore()
  const execution = useExecutionStore()
  const workspaces = useWorkspaceStore()
  const conversations = useConversationStore()

  const workspaceReadiness = computed(() => {
    if (!workspaces.hasWorkspace) return { state: 'no_workspace', ready: false }
    const readiness = workspaces.workspaceAIConfig?.readiness as Record<string, unknown> | undefined
    if (readiness && !readiness.credential_ready) return { state: 'model_connection_required', ready: false }
    if (readiness && (!readiness.model_ready || !readiness.configuration_reviewed)) {
      return { state: 'workspace_configuration_required', ready: false }
    }
    if (Number(workspaces.activeWorkspaceSummary?.table_count || 0) < 1) {
      return { state: 'no_data', ready: false }
    }
    return { state: 'ready', ready: true }
  })

  const canAnalyze = computed(() => {
    const readiness = workspaces.workspaceAIConfig?.readiness as Record<string, unknown> | undefined
    const providerReady = readiness
      ? Boolean(readiness.credential_ready)
      : (preferences.providerRequiresApiKey ? preferences.selectedProviderApiKeyPresent : true)
    return providerReady && workspaceReadiness.value.ready
  })

  function clearWorkspaceSession() {
    conversations.reset()
    artifacts.reset()
    execution.pythonFileContent = ''
    execution.generatedCode = ''
    execution.runtimeError = ''
  }

  async function activateWorkspace(workspaceId: unknown) {
    clearWorkspaceSession()
    await workspaces.activateWorkspace(workspaceId)
    await conversations.fetchConversations(workspaces.activeWorkspaceId)
  }

  async function createWorkspace(name: unknown, context: unknown = '') {
    const workspace = await workspaces.createWorkspace(name, context)
    if (workspace?.id) await activateWorkspace(workspace.id)
    await workspaces.fetchWorkspaces()
    return workspace
  }

  async function deleteWorkspace(workspaceId: unknown) {
    const target = String(workspaceId || '').trim()
    const result = await workspaces.deleteWorkspace(target)
    artifacts.setSelectedTableArtifact(target, '')
    artifacts.setSelectedFigureArtifact(target, '')
    if (!workspaces.activeWorkspaceId && workspaces.workspaces.length > 0) {
      await activateWorkspace(workspaces.workspaces[0]?.id)
    } else if (!workspaces.activeWorkspaceId) {
      clearWorkspaceSession()
    }
    return result
  }

  function openDataConnectionFlow() {
    if (!workspaces.hasWorkspace) {
      ui.openSettings('workspace-general')
      return
    }
    ui.requestConnectionFlow()
  }

  return proxyRefs({
    workspaceReadiness,
    canAnalyze,
    activateWorkspace,
    createWorkspace,
    deleteWorkspace,
    openDataConnectionFlow,
    clearWorkspaceSession,
  })
}
