import { describe, expect, it } from 'vitest'
import { nextTick, ref } from 'vue'
import { useWorkspaceSettings } from '../src/composables/useWorkspaceSettings'

describe('workspace settings coordinator', () => {
  it('normalizes deep links and wraps keyboard section navigation', async () => {
    const initial = ref('data')
    const settings = useWorkspaceSettings(initial)
    expect(settings.activeWorkspaceSection.value).toBe('runtime')

    settings.moveWorkspaceSection(1)
    expect(settings.activeWorkspaceSection.value).toBe('ai')
    settings.moveWorkspaceSection(1)
    expect(settings.activeWorkspaceSection.value).toBe('general')

    initial.value = 'unsupported'
    await nextTick()
    expect(settings.activeWorkspaceSection.value).toBe('general')
  })
})
