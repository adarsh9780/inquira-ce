import { ref } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { connectionService } from '../src/services/connectionService'
import { useWorkspaceDataSources } from '../src/composables/useWorkspaceDataSources'

vi.mock('../src/composables/useToast', () => ({ toast: { success: vi.fn() } }))
vi.mock('../src/services/connectionService', () => ({
  connectionService: {
    list: vi.fn(), chooseFile: vi.fn(), discover: vi.fn(), preview: vi.fn(),
    create: vi.fn(), refresh: vi.fn(), remove: vi.fn(),
  },
}))

describe('useWorkspaceDataSources', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(connectionService.list).mockResolvedValue({ connections: [] })
  })

  it('discovers, previews, and creates a selected local source', async () => {
    const changed = vi.fn()
    vi.mocked(connectionService.chooseFile).mockResolvedValue({ source_path: '/tmp/book.xlsx', adapter_kind: 'excel' })
    vi.mocked(connectionService.discover).mockResolvedValue({ objects: [
      { id: 'sheet:Sales', name: 'Sales', metadata: { selectable: true } },
    ] })
    vi.mocked(connectionService.preview).mockResolvedValue({ columns: [{ name: 'amount' }], rows: [{ amount: 42 }] })
    vi.mocked(connectionService.create).mockResolvedValue({})
    const state = useWorkspaceDataSources(ref('workspace-1'), changed)

    expect(await state.chooseFile()).toBe(true)
    expect(state.pending.value).toMatchObject({
      adapterKind: 'excel', name: 'Sales', selectedObjectIds: ['sheet:Sales'], previewRows: [{ amount: 42 }],
    })
    expect(await state.create()).toBe(true)
    expect(connectionService.create).toHaveBeenCalledWith(expect.objectContaining({
      workspace_id: 'workspace-1', selected_object_ids: ['sheet:Sales'], options: { formula_mode: 'cached' },
    }))
    expect(state.pending.value).toBeNull()
    expect(changed).toHaveBeenCalledOnce()
  })

  it('keeps source errors local and does not create an incomplete draft', async () => {
    vi.mocked(connectionService.chooseFile).mockRejectedValue(new Error('picker failed'))
    const state = useWorkspaceDataSources(ref('workspace-1'))

    expect(await state.chooseFile()).toBe(false)
    expect(state.pending.value).toBeNull()
    expect(state.error.value).toContain('picker failed')
    expect(await state.create()).toBe(false)
    expect(connectionService.create).not.toHaveBeenCalled()
  })
})
