import { afterEach, describe, expect, it, vi } from 'vitest'

import { workspaceService } from '../src/services/workspaceService'

afterEach(() => {
  delete window.go
})

describe('workspaceService Wails bridge', () => {
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

    await workspaceService.list()
    await workspaceService.create('Finance', 'Fiscal calendar starts in April')
    await workspaceService.activate('workspace-1')
    await workspaceService.update('workspace-1', 'Finance 2026')
    await workspaceService.update('workspace-1', 'Finance', 'Updated context')
    await workspaceService.summary('workspace-1')
    await workspaceService.delete('workspace-1')
    const deletionJobs = await workspaceService.listDeletionJobs()

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
    expect(deletionJobs).toEqual({ jobs: [] })
  })
})
