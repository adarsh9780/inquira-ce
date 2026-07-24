import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'

import { useWorkspaceActivation } from '../src/composables/useWorkspaceActivation'
import { usePreferencesStore } from '../src/stores/preferencesStore'
import { useWorkspaceStore } from '../src/stores/workspaceStore'

describe('domain store state synchronization', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('derives data readiness only from the active workspace summary', () => {
    const store = useWorkspaceStore()
    const activation = useWorkspaceActivation()
    store.workspaces = [{ id: 'workspace-1', name: 'Workspace' }]
    store.activeWorkspaceId = 'workspace-1'
    store.activeWorkspaceSummary = {
      id: 'workspace-1',
      table_count: 0,
    }
    store.workspaceAIConfig = {
      readiness: {
        credential_ready: true,
        model_ready: true,
        configuration_reviewed: true,
      },
    }

    expect('dataFilePath' in store).toBe(false)
    expect('ingestedTableName' in store).toBe(false)
    expect('ingestedColumns' in store).toBe(false)
    expect('hasDataFile' in store).toBe(false)
    expect(activation.workspaceReadiness).toEqual({ state: 'no_data', ready: false })

    store.activeWorkspaceSummary = {
      id: 'workspace-1',
      table_count: 1,
      table_names: ['sales'],
    }
    expect(activation.workspaceReadiness).toEqual({ state: 'ready', ready: true })
  })

  it('applies saved request-warning and data-sample preferences immediately', () => {
    const store = usePreferencesStore()

    expect(store.applyPreferencesResponse).toBeTypeOf('function')
    store.applyPreferencesResponse({
      slow_request_warning_seconds: 45,
      allow_llm_data_samples: true,
    })

    expect(store.slowRequestWarningSeconds).toBe(45)
    expect(store.allowLlmDataSamples).toBe(true)
  })
})
