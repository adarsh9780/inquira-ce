import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useExecutionStore } from './executionStore'

describe('executionStore', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('tracks user edits against the current agent baseline', () => {
    const store = useExecutionStore()
    store.setGeneratedCode('print("agent")')
    store.noteUserEditedCode('print("user")')
    expect(store.hasUserEditedCode).toBe(true)
    expect(store.codeEditorSource).toBe('user')
    store.noteUserEditedCode('print("agent")')
    expect(store.hasUserEditedCode).toBe(false)
    expect(store.codeEditorSource).toBe('agent')
  })

  it('normalizes runtime status per workspace', () => {
    const store = useExecutionStore()
    store.setWorkspaceRuntimeStatus('workspace-a', 'READY')
    store.setWorkspaceRuntimeStatus('workspace-b', 'unexpected')
    expect(store.getWorkspaceRuntimeStatus('workspace-a')).toBe('ready')
    expect(store.getWorkspaceRuntimeStatus('workspace-b')).toBe('missing')
    expect(store.getWorkspaceRuntimeStatus('')).toBe('missing')
  })

  it('caps terminal history and records how many entries were trimmed', () => {
    const store = useExecutionStore()
    for (let index = 0; index < 55; index += 1) {
      store.appendTerminalEntry({ id: `entry-${index}`, stdout: String(index) })
    }
    expect(store.terminalEntries).toHaveLength(50)
    expect(store.terminalEntries[0]).toMatchObject({ id: 'entry-5' })
    expect(store.terminalEntriesTrimmedCount).toBe(5)
  })

  it('trims very large terminal streams from the beginning', () => {
    const store = useExecutionStore()
    store.appendTerminalEntry({ id: 'large', stdout: `prefix${'x'.repeat(200_000)}` })
    const entry = store.terminalEntries[0] as Record<string, unknown>
    expect(String(entry.stdout)).toHaveLength(200_000)
    expect(String(entry.stdout).startsWith('prefix')).toBe(false)
  })
})
