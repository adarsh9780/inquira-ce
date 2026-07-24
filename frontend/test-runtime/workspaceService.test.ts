import { afterEach, describe, expect, it, vi } from 'vitest'

import { workspaceApi } from '../src/api/workspaces'

afterEach(() => {
  delete window.go
})

describe('workspaceApi Wails bridge', () => {
  it('routes workspace metadata operations directly to Go', async () => {
    const app = {
      ListWorkspaces: vi.fn().mockResolvedValue({ workspaces: [] }),
      CreateWorkspace: vi.fn().mockResolvedValue({ id: 'workspace-1' }),
      ActivateWorkspace: vi.fn().mockResolvedValue({ id: 'workspace-1', is_active: true }),
      UpdateWorkspace: vi.fn().mockResolvedValue({ id: 'workspace-1', name: 'Finance' }),
      GetWorkspaceSummary: vi.fn().mockResolvedValue({ id: 'workspace-1', table_count: 0 }),
      DeleteWorkspace: vi.fn().mockResolvedValue({ job_id: 'job-1', status: 'completed' }),
    }
    window.go = { main: { App: app } }

    await workspaceApi.list()
    await workspaceApi.create('Finance', 'Fiscal calendar starts in April')
    await workspaceApi.activate('workspace-1')
    await workspaceApi.update('workspace-1', 'Finance 2026')
    await workspaceApi.update('workspace-1', 'Finance', 'Updated context')
    await workspaceApi.summary('workspace-1')
    await workspaceApi.remove('workspace-1')

    expect(app.ListWorkspaces).toHaveBeenCalledOnce()
    expect(app.CreateWorkspace).toHaveBeenCalledWith({
      name: 'Finance',
      schema_context: 'Fiscal calendar starts in April',
    })
    expect(app.ActivateWorkspace).toHaveBeenCalledWith('workspace-1')
    expect(app.UpdateWorkspace).toHaveBeenNthCalledWith(1, {
      workspace_id: 'workspace-1',
      name: 'Finance 2026',
    })
    expect(app.UpdateWorkspace).toHaveBeenNthCalledWith(2, {
      workspace_id: 'workspace-1',
      name: 'Finance',
      schema_context: 'Updated context',
    })
    expect(app.GetWorkspaceSummary).toHaveBeenCalledWith('workspace-1')
    expect(app.DeleteWorkspace).toHaveBeenCalledWith('workspace-1')
  })
})
