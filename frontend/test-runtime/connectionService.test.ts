import { afterEach, describe, expect, it, vi } from 'vitest'

import { connectionService } from '../src/services/connectionService.ts'

afterEach(() => {
  delete window.go
})

describe('connectionService Wails bridge', () => {
  it('routes the local connection lifecycle directly to Go', async () => {
    const app = {
      ListConnections: vi.fn().mockResolvedValue({ connections: [] }),
      DiscoverLocalConnection: vi.fn().mockResolvedValue({ objects: [{ id: 'file' }] }),
      PreviewLocalConnection: vi.fn().mockResolvedValue({ rows: [{ id: 1 }] }),
      CreateLocalConnection: vi.fn().mockResolvedValue({ id: 'connection-1', status: 'ready' }),
      RefreshConnection: vi.fn().mockResolvedValue({ id: 'connection-1', status: 'ready' }),
      DeleteConnection: vi.fn().mockResolvedValue({ deleted: true }),
    }
    window.go = { main: { App: app } }

    await connectionService.list('workspace-1')
    await connectionService.discover('csv', '/tmp/sales.csv')
    await connectionService.preview('excel', '/tmp/book.xlsx', 'sheet:Sales', 25, { formula_mode: 'cached' })
    await connectionService.create({
      workspace_id: 'workspace-1',
      name: 'Sales',
      adapter_kind: 'csv',
      source_path: '/tmp/sales.csv',
      selected_object_ids: ['file'],
    })
    await connectionService.refresh('connection-1')
    await connectionService.remove('connection-1')

    expect(app.ListConnections).toHaveBeenCalledWith('workspace-1')
    expect(app.DiscoverLocalConnection).toHaveBeenCalledWith({ adapter_kind: 'csv', source_path: '/tmp/sales.csv' })
    expect(app.PreviewLocalConnection).toHaveBeenCalledWith({
      adapter_kind: 'excel',
      source_path: '/tmp/book.xlsx',
      source_object_id: 'sheet:Sales',
      limit: 25,
      options: { formula_mode: 'cached' },
    })
    expect(app.CreateLocalConnection).toHaveBeenCalledWith(expect.objectContaining({ name: 'Sales', selected_object_ids: ['file'] }))
    expect(app.RefreshConnection).toHaveBeenCalledWith('connection-1')
    expect(app.DeleteConnection).toHaveBeenCalledWith('connection-1')
  })
})
