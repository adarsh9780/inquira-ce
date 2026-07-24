import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useAppCoordinatorStore } from '../src/stores/appCoordinatorStore'
import { useArtifactStore } from '../src/stores/artifactStore'
import { useConversationStore } from '../src/stores/conversationStore'
import { useExecutionStore } from '../src/stores/executionStore'
import { usePreferencesStore } from '../src/stores/preferencesStore'
import { useUiStore } from '../src/stores/uiStore'
import { useWorkspaceStore } from '../src/stores/workspaceStore'

describe('domain store ownership', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('keeps the compatibility coordinator wired to each domain store', () => {
    const app = useAppCoordinatorStore()
    const preferences = usePreferencesStore()
    const workspace = useWorkspaceStore()
    const conversation = useConversationStore()
    const artifacts = useArtifactStore()
    const execution = useExecutionStore()
    const ui = useUiStore()

    app.setSelectedModel('openrouter/free')
    app.setActiveWorkspaceId('workspace-1')
    app.addQuestionHistoryEntry('Summarize revenue')
    app.setDataframeCount(3)
    app.setRuntimeError('runtime unavailable')
    app.setSidebarCollapsed(true)

    expect(preferences.selectedModel).toBe('openrouter/free')
    expect(workspace.activeWorkspaceId).toBe('workspace-1')
    expect(conversation.questionHistory).toEqual(['Summarize revenue'])
    expect(artifacts.dataframeCount).toBe(3)
    expect(execution.runtimeError).toBe('runtime unavailable')
    expect(ui.isSidebarCollapsed).toBe(true)
  })

  it('does not duplicate state between store instances', () => {
    const firstWorkspace = useWorkspaceStore()
    const secondWorkspace = useWorkspaceStore()

    firstWorkspace.activeWorkspaceId = 'workspace-shared'

    expect(secondWorkspace.activeWorkspaceId).toBe('workspace-shared')
  })
})
