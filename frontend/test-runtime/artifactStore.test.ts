import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useArtifactStore } from '../src/stores/artifactStore'

describe('artifactStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('normalizes artifact collections and keeps counts synchronized', () => {
    const store = useArtifactStore()

    store.setDataframes([{ name: 'orders' }])
    store.setFigures([{ name: 'trend', data: { data: [{ x: [1], y: [2] }], layout: {} } }])

    expect(store.dataframeCount).toBe(1)
    expect(store.figureCount).toBe(1)

    store.removeResultArtifact('missing')
    expect(store.dataframeCount).toBe(1)
    expect(store.figureCount).toBe(1)
  })

  it('scopes selections and pages by workspace and turn', () => {
    const store = useArtifactStore()
    const persist = vi.fn()
    store.configurePersistence(persist)

    store.setSelectedTableArtifact('workspace-1', 'table-1', 'turn-1')
    store.setSelectedFigureArtifact('workspace-1', 'figure-1', 'turn-1')
    store.setTablePageOffset('workspace-1', 'table-1', 3, 'turn-1')

    expect(store.getSelectedTableArtifact('workspace-1', 'turn-1')).toBe('table-1')
    expect(store.getSelectedTableArtifact('workspace-1', 'turn-2')).toBe('')
    expect(store.getSelectedFigureArtifact('workspace-1', 'turn-1')).toBe('figure-1')
    expect(store.getTablePageOffset('workspace-1', 'table-1', 'turn-1')).toBe(3)
    expect(persist).toHaveBeenCalledTimes(3)
  })

  it('avoids redundant viewport and page mutations', () => {
    const store = useArtifactStore()
    const persist = vi.fn()
    store.configurePersistence(persist)

    store.setTableViewport(1, 100, 240)
    store.setTableViewport(1, 100, 240)
    expect([store.tableWindowStart, store.tableWindowEnd, store.tableRowCount]).toEqual([1, 100, 240])

    store.setTablePageOffset('workspace-1', 'table-1', 0, 'turn-1')
    expect(persist).not.toHaveBeenCalled()
  })
})
