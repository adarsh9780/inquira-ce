import { afterEach, describe, expect, it, vi } from 'vitest'

import { catalogService } from '../src/services/catalogService'

afterEach(() => {
  delete window.go
})

describe('catalogService Wails bridge', () => {
  it('prepares the active workspace analysis catalog through Go', async () => {
    const app = {
      PrepareWorkspaceCatalog: vi.fn().mockResolvedValue({
        workspace_id: 'workspace-1',
        database_path: '/data/workspaces/workspace-1/workspace.duckdb',
        tables: [{ id: 'table-1', name: 'sales_data' }],
      }),
    }
    window.go = { main: { App: app } }

    const result = await catalogService.prepare('workspace-1')

    expect(app.PrepareWorkspaceCatalog).toHaveBeenCalledWith('workspace-1')
    expect(result.tables).toHaveLength(1)
  })
})
