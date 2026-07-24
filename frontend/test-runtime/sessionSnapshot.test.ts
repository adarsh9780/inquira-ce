import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useSessionSnapshot } from '../src/composables/useSessionSnapshot'
import { usePreferencesStore } from '../src/stores/preferencesStore'
import { useWorkspaceStore } from '../src/stores/workspaceStore'

describe('session snapshot coordinator', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('hydrates domain stores and excludes API key material from snapshots', () => {
    const coordinator = useSessionSnapshot()
    const preferences = usePreferencesStore()
    const workspaces = useWorkspaceStore()
    preferences.apiKey = 'secret'
    preferences.setSelectedModel('model-a')
    workspaces.setActiveWorkspaceId('workspace-a')
    const snapshot = coordinator.buildSnapshot()
    expect(JSON.stringify(snapshot)).not.toContain('secret')
    coordinator.reset()
    expect(coordinator.applySnapshot(snapshot)).toBe(true)
    expect(preferences.selectedModel).toBe('model-a')
    expect(workspaces.activeWorkspaceId).toBe('workspace-a')
  })
})
