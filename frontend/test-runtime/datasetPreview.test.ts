import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { workspaceApi } from '../src/api/workspaces'
import {
  clearDatasetPreviewCache,
  loadDatasetPreview,
  normalizeDatasetPreview,
} from '../src/composables/useDatasetPreview'
import TableDataPreview from '../src/components/schema/TableDataPreview.vue'

describe('workspace dataset preview cache', () => {
  beforeEach(() => {
    clearDatasetPreviewCache('workspace-1')
    vi.restoreAllMocks()
  })

  afterEach(() => {
    delete window.go
  })

  it('deduplicates and session-caches each table edge until the workspace changes', async () => {
    const preview = vi.spyOn(workspaceApi, 'previewDataset').mockResolvedValue({
      table_name: 'sales',
      columns: ['id'],
      rows: [{ id: 1 }],
      row_count: 1,
      mode: 'head',
      offset: 0,
      limit: 100,
    })

    const [first, second] = await Promise.all([
      loadDatasetPreview('workspace-1', 'sales', 'head'),
      loadDatasetPreview('workspace-1', 'sales', 'head'),
    ])
    const cached = await loadDatasetPreview('workspace-1', 'sales', 'head')

    expect(preview).toHaveBeenCalledTimes(1)
    expect(first).toEqual(second)
    expect(cached.rows).toEqual([{ id: 1 }])

    clearDatasetPreviewCache('workspace-1')
    await loadDatasetPreview('workspace-1', 'sales', 'head')
    expect(preview).toHaveBeenCalledTimes(2)
  })

  it('normalizes malformed bridge fields into a safe table payload', () => {
    expect(normalizeDatasetPreview({
      columns: ['id', '', 42],
      rows: [{ id: 1 }, null],
      row_count: -5,
      offset: -2,
      limit: 500,
    }, 'sales', 'tail')).toEqual({
      tableName: 'sales',
      columns: ['id', '42'],
      rows: [{ id: 1 }, {}],
      rowCount: 0,
      mode: 'tail',
      offset: 0,
      limit: 100,
    })
  })

  it('loads lazily on mount and switches the shared table between first and last rows', async () => {
    const app = {
      PreviewWorkspaceDataset: vi.fn().mockImplementation(
        async (_workspaceId: string, _tableName: string, mode: string) => ({
          table_name: 'sales',
          columns: ['id'],
          rows: [{ id: mode === 'tail' ? 105 : 1 }],
          row_count: 105,
          mode,
          offset: mode === 'tail' ? 5 : 0,
          limit: 100,
        }),
      ),
    }
    window.go = { main: { App: app } }

    const wrapper = mount(TableDataPreview, {
      props: {
        workspaceId: 'workspace-1',
        table: {
          id: 'table-1',
          tableName: 'sales',
          rowCount: 105,
          status: 'ready',
          columns: [],
        },
      },
    })
    await flushPromises()

    expect(app.PreviewWorkspaceDataset).toHaveBeenCalledWith('workspace-1', 'sales', 'head')
    expect(wrapper.text()).toContain('Rows 1–1 of 105')

    await wrapper.get('button[title="Last 100"]').trigger('click')
    await flushPromises()

    expect(app.PreviewWorkspaceDataset).toHaveBeenLastCalledWith('workspace-1', 'sales', 'tail')
    expect(wrapper.text()).toContain('Rows 6–6 of 105')
    expect(wrapper.find('[data-inquira-data-grid]').exists()).toBe(true)
  })
})
