import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'

import { useAppStore } from '../src/stores/appStore'

describe('app store state synchronization', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('derives data readiness only from the active workspace summary', () => {
    const store = useAppStore()
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
    expect(store.workspaceReadiness).toEqual({ state: 'no_data', ready: false })

    store.activeWorkspaceSummary = {
      id: 'workspace-1',
      table_count: 1,
      table_names: ['sales'],
    }
    expect(store.workspaceReadiness).toEqual({ state: 'ready', ready: true })
  })

  it('applies saved request-warning and data-sample preferences immediately', () => {
    const store = useAppStore()

    expect(store.applyPreferencesResponse).toBeTypeOf('function')
    store.applyPreferencesResponse({
      slow_request_warning_seconds: 45,
      allow_llm_data_samples: true,
    })

    expect(store.slowRequestWarningSeconds).toBe(45)
    expect(store.allowLlmDataSamples).toBe(true)
  })
})
