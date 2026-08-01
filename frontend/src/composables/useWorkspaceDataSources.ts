import { computed, ref, watch, type Ref } from 'vue'

import { connectionService } from '../services/connectionService'
import { toast } from './useToast'
import { extractApiErrorMessage } from '../utils/apiError'
import { filenameFromPath } from '../utils/pathUtils'

type NativeRecord = Record<string, any>

export interface PendingDataSource {
  sourcePath: string
  adapterKind: string
  name: string
  objects: NativeRecord[]
  selectedObjectIds: string[]
  activeObjectId: string
  formulaMode: 'cached' | 'formula'
  columns: NativeRecord[]
  previewRows: NativeRecord[]
}

export function useWorkspaceDataSources(
  workspaceId: Ref<unknown>,
  onChanged: () => void | Promise<void> = () => undefined,
) {
  const connections = ref<NativeRecord[]>([])
  const pending = ref<PendingDataSource | null>(null)
  const busy = ref(false)
  const error = ref('')
  const objectSearch = ref('')
  const refreshingIds = ref(new Set<string>())

  const filteredObjects = computed(() => {
    const query = objectSearch.value.trim().toLowerCase()
    const objects = pending.value?.objects || []
    return query
      ? objects.filter((item) => String(item.name || item.id || '').toLowerCase().includes(query))
      : objects
  })
  const selectableObjects = computed(() => (
    (pending.value?.objects || []).filter((item) => item?.metadata?.selectable !== false)
  ))

  async function load() {
    const id = String(workspaceId.value || '').trim()
    if (!id) {
      connections.value = []
      return
    }
    try {
      const response = await connectionService.list(id) as NativeRecord
      if (id === String(workspaceId.value || '').trim()) {
        connections.value = Array.isArray(response?.connections) ? response.connections : []
      }
    } catch (cause) {
      error.value = extractApiErrorMessage(cause, 'Could not load data sources.')
    }
  }

  async function chooseFile() {
    if (busy.value) return false
    error.value = ''
    busy.value = true
    try {
      const selection = await connectionService.chooseFile() as NativeRecord
      const sourcePath = String(selection?.source_path || '').trim()
      const adapterKind = String(selection?.adapter_kind || '').trim().toLowerCase()
      if (!sourcePath || !adapterKind) return false
      const discovery = await connectionService.discover(adapterKind, sourcePath) as NativeRecord
      const objects = Array.isArray(discovery?.objects) ? discovery.objects : []
      const firstObject = objects.find((item) => item?.metadata?.selectable !== false) || objects[0] || {}
      const activeObjectId = isObjectSelectionAdapter(adapterKind) ? String(firstObject?.id || '') : ''
      const options = adapterKind === 'excel' ? { formula_mode: 'cached' } : {}
      const preview = activeObjectId || !isObjectSelectionAdapter(adapterKind)
        ? await connectionService.preview(adapterKind, sourcePath, activeObjectId, 25, options) as NativeRecord
        : { columns: [], rows: [] }
      objectSearch.value = ''
      pending.value = {
        sourcePath,
        adapterKind,
        name: String(adapterKind === 'sqlite' ? filenameFromPath(sourcePath) : (firstObject?.name || filenameFromPath(sourcePath, 'Local connection'))).trim(),
        objects,
        selectedObjectIds: firstObject?.metadata?.selectable === false ? [] : [String(firstObject?.id || 'file')],
        activeObjectId: String(firstObject?.id || ''),
        formulaMode: 'cached',
        columns: Array.isArray(preview?.columns) ? preview.columns : (firstObject?.columns || []),
        previewRows: Array.isArray(preview?.rows) ? preview.rows : [],
      }
      return true
    } catch (cause) {
      error.value = extractApiErrorMessage(cause, 'Could not inspect the selected file.')
      return false
    } finally {
      busy.value = false
    }
  }

  async function previewObject(objectId: unknown) {
    const draft = pending.value
    const id = String(objectId || '').trim()
    if (!draft || !id || busy.value) return
    error.value = ''
    busy.value = true
    try {
      const options = draft.adapterKind === 'excel' ? { formula_mode: draft.formulaMode } : {}
      const preview = await connectionService.preview(draft.adapterKind, draft.sourcePath, id, 25, options) as NativeRecord
      draft.activeObjectId = id
      draft.columns = Array.isArray(preview?.columns) ? preview.columns : []
      draft.previewRows = Array.isArray(preview?.rows) ? preview.rows : []
    } catch (cause) {
      error.value = extractApiErrorMessage(cause, 'Could not preview the selected source.')
    } finally {
      busy.value = false
    }
  }

  async function create() {
    const id = String(workspaceId.value || '').trim()
    const draft = pending.value
    if (!id || !draft || busy.value || !draft.name.trim() || draft.selectedObjectIds.length === 0) return false
    error.value = ''
    busy.value = true
    try {
      await connectionService.create({
        workspace_id: id,
        name: draft.name.trim(),
        adapter_kind: draft.adapterKind,
        source_path: draft.sourcePath,
        selected_object_ids: draft.selectedObjectIds,
        options: draft.adapterKind === 'excel' ? { formula_mode: draft.formulaMode } : {},
      })
      pending.value = null
      objectSearch.value = ''
      await load()
      await onChanged()
      toast.success('Data source added', 'The local snapshot is ready for analysis.')
      return true
    } catch (cause) {
      error.value = extractApiErrorMessage(cause, 'Could not add the data source.')
      return false
    } finally {
      busy.value = false
    }
  }

  async function refreshConnection(connectionId: unknown) {
    const id = String(connectionId || '').trim()
    if (!id || refreshingIds.value.has(id)) return
    refreshingIds.value = new Set(refreshingIds.value).add(id)
    error.value = ''
    try {
      await connectionService.refresh(id)
      await load()
      await onChanged()
      toast.success('Data source refreshed', 'The local snapshot is up to date.')
    } catch (cause) {
      error.value = extractApiErrorMessage(cause, 'Could not refresh the data source.')
      await load()
    } finally {
      const next = new Set(refreshingIds.value)
      next.delete(id)
      refreshingIds.value = next
    }
  }

  async function removeConnection(connectionId: unknown) {
    const id = String(connectionId || '').trim()
    if (!id || busy.value) return
    error.value = ''
    busy.value = true
    try {
      await connectionService.remove(id)
      await load()
      await onChanged()
      toast.success('Data source removed', 'Its local snapshots were removed from this workspace.')
    } catch (cause) {
      error.value = extractApiErrorMessage(cause, 'Could not remove the data source.')
    } finally {
      busy.value = false
    }
  }

  function cancelPending() {
    if (busy.value) return
    pending.value = null
    objectSearch.value = ''
    error.value = ''
  }

  function selectAllObjects() {
    if (pending.value) pending.value.selectedObjectIds = selectableObjects.value.map((item) => String(item.id))
  }

  function clearObjectSelection() {
    if (pending.value) pending.value.selectedObjectIds = []
  }

  watch(workspaceId, () => {
    pending.value = null
    error.value = ''
    void load()
  }, { immediate: true })

  return {
    connections,
    pending,
    busy,
    error,
    objectSearch,
    refreshingIds,
    filteredObjects,
    selectableObjects,
    load,
    chooseFile,
    previewObject,
    create,
    refreshConnection,
    removeConnection,
    cancelPending,
    selectAllObjects,
    clearObjectSelection,
  }
}

export function isObjectSelectionAdapter(kind: unknown) {
  return kind === 'excel' || kind === 'sqlite'
}

export function dataSourceKindLabel(kind: unknown) {
  const normalized = String(kind || '').toLowerCase()
  if (normalized === 'csv') return 'CSV'
  if (normalized === 'excel') return 'Excel'
  if (normalized === 'json') return 'JSON'
  if (normalized === 'sqlite') return 'SQLite'
  return 'Parquet'
}

export function dataSourceSummary(connection: NativeRecord) {
  const outputs = Array.isArray(connection?.outputs) ? connection.outputs : []
  const rows = outputs.reduce((total, output) => total + Number(output?.row_count || 0), 0)
  return `${dataSourceKindLabel(connection?.adapter_kind)} · ${outputs.length} table${outputs.length === 1 ? '' : 's'} · ${rows.toLocaleString()} rows`
}

export function sourceObjectSummary(object: NativeRecord, adapterKind: unknown) {
  const columns = Number(object?.metadata?.column_count ?? object?.columns?.length ?? 0)
  if (adapterKind === 'sqlite') return `${object?.kind || 'table'} · ${columns} columns`
  return `${object?.metadata?.visibility || 'visible'} · ${Number(object?.metadata?.row_count || 0).toLocaleString()} rows · ${columns} columns`
}
