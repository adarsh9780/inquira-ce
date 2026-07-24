import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useWorkspaceActivation } from '../src/composables/useWorkspaceActivation'
import { usePreferencesStore } from '../src/stores/preferencesStore'
import { useWorkspaceStore } from '../src/stores/workspaceStore'

describe('workspace activation coordinator', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('derives readiness across workspace and preference domains', () => {
    const workspaces = useWorkspaceStore()
    const preferences = usePreferencesStore()
    const activation = useWorkspaceActivation()
    workspaces.workspaces = [{ id: 'workspace-a', name: 'Sales', table_count: 1, table_names: ['orders'] }]
    workspaces.activeWorkspaceId = 'workspace-a'
    workspaces.activeWorkspaceSummary = workspaces.workspaces[0]
    preferences.providerRequiresApiKey = false
    expect(activation.workspaceReadiness).toEqual({ state: 'ready', ready: true })
    expect(activation.canAnalyze).toBe(true)
  })
})
