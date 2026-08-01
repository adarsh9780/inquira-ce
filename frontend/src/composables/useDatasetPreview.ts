import { ref } from 'vue'

import { workspaceApi } from '../api/workspaces'
import type { DatasetPreview, DatasetPreviewMode } from '../types/datasetPreview'

const previewCache = new Map<string, DatasetPreview>()
const previewRequests = new Map<string, Promise<DatasetPreview>>()
const workspaceRevisions = new Map<string, number>()

function previewKey(workspaceId: string, tableName: string, mode: DatasetPreviewMode) {
  return `${workspaceId}\u0000${tableName}\u0000${mode}`
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {}
}

function finiteNumber(value: unknown, fallback = 0) {
  const number = Number(value)
  return Number.isFinite(number) ? number : fallback
}

export function normalizeDatasetPreview(
  value: unknown,
  tableName: string,
  mode: DatasetPreviewMode,
): DatasetPreview {
  const source = asRecord(value)
  const columns = Array.isArray(source.columns)
    ? source.columns.map((column) => String(column)).filter(Boolean)
    : []
  const rows = Array.isArray(source.rows)
    ? source.rows.map(asRecord)
    : []
  return {
    tableName: String(source.table_name || tableName),
    columns,
    rows,
    rowCount: Math.max(0, finiteNumber(source.row_count)),
    mode: source.mode === 'tail' ? 'tail' : mode,
    offset: Math.max(0, finiteNumber(source.offset)),
    limit: Math.max(1, Math.min(100, finiteNumber(source.limit, 100))),
  }
}

export function clearDatasetPreviewCache(workspaceId: string, tableName = '') {
	const prefix = tableName
	  ? `${workspaceId}\u0000${tableName}\u0000`
	  : `${workspaceId}\u0000`
	for (const key of previewCache.keys()) {
	  if (key.startsWith(prefix)) previewCache.delete(key)
	}
	for (const key of previewRequests.keys()) {
	  if (key.startsWith(prefix)) previewRequests.delete(key)
	}
  workspaceRevisions.set(workspaceId, (workspaceRevisions.get(workspaceId) || 0) + 1)
}

export function loadDatasetPreview(
  workspaceId: string,
  tableName: string,
  mode: DatasetPreviewMode,
): Promise<DatasetPreview> {
  const key = previewKey(workspaceId, tableName, mode)
  const cached = previewCache.get(key)
  if (cached) return Promise.resolve(cached)
  const pending = previewRequests.get(key)
  if (pending) return pending

  const revision = workspaceRevisions.get(workspaceId) || 0
  const request = workspaceApi.previewDataset(workspaceId, tableName, mode)
    .then((value) => normalizeDatasetPreview(value, tableName, mode))
    .then((preview) => {
      if ((workspaceRevisions.get(workspaceId) || 0) === revision) {
        previewCache.set(key, preview)
      }
      return preview
    })
    .finally(() => {
      if (previewRequests.get(key) === request) previewRequests.delete(key)
    })
  previewRequests.set(key, request)
  return request
}

export function useDatasetPreview() {
  const preview = ref<DatasetPreview | null>(null)
  const isLoading = ref(false)
  const error = ref('')
  let activeRequest = 0

  async function load(workspaceId: string, tableName: string, mode: DatasetPreviewMode) {
    const requestId = ++activeRequest
    isLoading.value = true
    error.value = ''
    try {
      const result = await loadDatasetPreview(workspaceId, tableName, mode)
      if (requestId === activeRequest) preview.value = result
      return result
    } catch (reason) {
      if (requestId === activeRequest) {
        preview.value = null
        error.value = reason instanceof Error ? reason.message : String(reason || 'Unable to load preview.')
      }
      return null
    } finally {
      if (requestId === activeRequest) isLoading.value = false
    }
  }

  return { preview, isLoading, error, load }
}
