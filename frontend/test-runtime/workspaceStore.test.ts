import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useWorkspaceStore } from '../src/stores/workspaceStore'

const bridge = {
  ListWorkspaces: vi.fn(),
  GetWorkspaceSummary: vi.fn(),
  GetWorkspaceAIConfig: vi.fn(),
  ActivateWorkspace: vi.fn(),
  CreateWorkspace: vi.fn(),
  UpdateWorkspace: vi.fn(),
  DeleteWorkspace: vi.fn(),
  ListWorkspaceDatasets: vi.fn(),
  GetWorkspaceDatasetSchema: vi.fn(),
}

describe('workspaceStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    window.go = { main: { App: bridge } }
    bridge.ListWorkspaces.mockResolvedValue({ workspaces: [] })
    bridge.GetWorkspaceSummary.mockResolvedValue(null)
    bridge.GetWorkspaceAIConfig.mockResolvedValue(null)
  })

  it('hydrates every workspace from the native list response', async () => {
    const store = useWorkspaceStore()
    bridge.ListWorkspaces.mockResolvedValue({
      workspaces: [
        { id: 'workspace-a', name: 'Sales', is_active: false },
        { id: 'workspace-b', name: 'Finance', is_active: true },
        { id: 'workspace-c', name: 'Operations', is_active: false },
      ],
    })
    bridge.GetWorkspaceSummary.mockResolvedValue({ id: 'workspace-b', table_count: 0 })

    await expect(store.fetchWorkspaces()).resolves.toHaveLength(3)

    expect(store.workspaces.map((workspace) => workspace.name)).toEqual([
      'Sales',
      'Finance',
      'Operations',
    ])
    expect(store.activeWorkspaceId).toBe('workspace-b')
  })

  it('recovers a stale active workspace from the native list', async () => {
    const store = useWorkspaceStore()
    store.setActiveWorkspaceId('missing')
    bridge.ListWorkspaces.mockResolvedValue({
      workspaces: [{ id: 'workspace-a', name: 'Sales' }],
    })
    bridge.GetWorkspaceSummary.mockResolvedValue({ id: 'workspace-a', table_count: 1 })
    await store.fetchWorkspaces()
    expect(store.activeWorkspaceId).toBe('workspace-a')
    expect(store.activeWorkspaceSummary).toMatchObject({ id: 'workspace-a' })
  })

  it('loads catalog columns from every saved dataset schema', async () => {
    const store = useWorkspaceStore()
    store.setActiveWorkspaceId('workspace-a')
    bridge.ListWorkspaceDatasets.mockResolvedValue({
      datasets: [{ table_name: 'orders' }, { table_name: 'customers' }],
    })
    bridge.GetWorkspaceDatasetSchema
      .mockResolvedValueOnce({ table_name: 'orders', columns: [{ name: 'amount', dtype: 'DOUBLE' }] })
      .mockResolvedValueOnce({ table_name: 'customers', columns: [{ name: 'name', dtype: 'VARCHAR' }] })
    await expect(store.fetchColumnCatalog()).resolves.toEqual([
      { table_name: 'orders', column_name: 'amount', dtype: 'DOUBLE' },
      { table_name: 'customers', column_name: 'name', dtype: 'VARCHAR' },
    ])
  })
})
