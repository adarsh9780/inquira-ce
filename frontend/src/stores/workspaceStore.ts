import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import type { WorkspaceSummary } from '../types/workspace'
import { workspaceApi } from '../api/workspaces'

type WorkspaceRecord = WorkspaceSummary & {
  schema_context?: string
  table_count?: number
}

type ColumnCatalogEntry = {
  table_name?: string
  column_name?: string
  dtype?: string
  [key: string]: unknown
}

export interface WorkspaceAIConfig {
  defaults?: {
    provider?: string
    main_model?: string
    lite_model?: string
    coding_model?: string
  }
  effective?: {
    provider?: string
    main_model?: string
    lite_model?: string
    coding_model?: string
  }
  overrides?: {
    provider?: string | null
    main_model?: string | null
    lite_model?: string | null
    coding_model?: string | null
    temperature?: number | null
    max_tokens?: number | null
    top_p?: number | null
    allow_llm_data_samples?: boolean
  }
  readiness?: {
    ready?: boolean
    credential_ready?: boolean
    [key: string]: unknown
  }
  [key: string]: unknown
}

export const useWorkspaceStore = defineStore('workspaces', () => {
  const columnCatalog = ref<ColumnCatalogEntry[]>([])
  const workspaces = ref<WorkspaceRecord[]>([])
  const activeWorkspaceSummary = ref<WorkspaceRecord | null>(null)
  const workspaceAIConfig = ref<WorkspaceAIConfig | null>(null)
  const activeWorkspaceId = ref('')
  const isLoadingWorkspaces = ref(false)
  const workspaceError = ref('')

  const schemaContext = computed(() => {
    const activeId = String(activeWorkspaceId.value || '').trim()
    const summary = activeWorkspaceSummary.value
    if (summary && String(summary.id || '').trim() === activeId) {
      return String(summary.schema_context || '')
    }
    const workspace = workspaces.value.find(
      (item) => String(item?.id || '').trim() === activeId,
    )
    return String(workspace?.schema_context || '')
  })

  const hasWorkspace = computed(() => {
    const activeId = String(activeWorkspaceId.value || '').trim()
    return Boolean(activeId && workspaces.value.some((workspace) => String(workspace.id) === activeId))
  })

  function setColumnCatalog(columns: unknown) {
    columnCatalog.value = Array.isArray(columns) ? columns as ColumnCatalogEntry[] : []
  }

  function setActiveWorkspaceId(workspaceId: unknown) {
    activeWorkspaceId.value = String(workspaceId || '').trim()
  }

  function clearWorkspaceDetail() {
    activeWorkspaceSummary.value = null
    workspaceAIConfig.value = null
    columnCatalog.value = []
  }

  async function fetchWorkspaceSummary(workspaceId: unknown = activeWorkspaceId.value) {
    const target = String(workspaceId || '').trim()
    if (!target) {
      activeWorkspaceSummary.value = null
      return null
    }
    try {
      const summary = await workspaceApi.summary(target) as unknown as WorkspaceRecord
      if (target === activeWorkspaceId.value) activeWorkspaceSummary.value = summary
      return summary
    } catch {
      if (target === activeWorkspaceId.value) activeWorkspaceSummary.value = null
      return null
    }
  }

  async function fetchWorkspaceAIConfig(workspaceId: unknown = activeWorkspaceId.value) {
    const target = String(workspaceId || '').trim()
    if (!target) {
      workspaceAIConfig.value = null
      return null
    }
    const config = await workspaceApi.getAIConfig(target) as WorkspaceAIConfig
    if (target === activeWorkspaceId.value) workspaceAIConfig.value = config
    return config
  }

  async function saveWorkspaceAIConfig(
    payload: Record<string, unknown>,
    workspaceId: unknown = activeWorkspaceId.value,
  ) {
    const target = String(workspaceId || '').trim()
    if (!target) throw new Error('Select a workspace before updating AI settings.')
    const config = await workspaceApi.updateAIConfig(target, payload) as WorkspaceAIConfig
    if (target === activeWorkspaceId.value) workspaceAIConfig.value = config
    return config
  }

  async function fetchColumnCatalog(options: { force?: boolean } = {}) {
    const workspaceId = String(activeWorkspaceId.value || '').trim()
    if (!workspaceId) {
      columnCatalog.value = []
      return []
    }
    if (!options.force && columnCatalog.value.length > 0) return columnCatalog.value
    try {
      const response = await workspaceApi.listDatasets(workspaceId)
      const datasets = Array.isArray(response?.datasets) ? response.datasets : []
      const schemas = await Promise.allSettled(datasets.map(async (value) => {
        const dataset = value as Record<string, unknown>
        const tableName = String(dataset.table_name || '').trim()
        if (!tableName) return []
        const schema = await workspaceApi.getDatasetSchema(workspaceId, tableName)
        return (Array.isArray(schema?.columns) ? schema.columns : [])
          .map((columnValue) => {
            const column = columnValue as Record<string, unknown>
            return {
              table_name: String(schema?.table_name || tableName).trim(),
              column_name: String(column.name || column.column_name || '').trim(),
              dtype: String(column.dtype || column.type || ''),
            }
          })
          .filter((column) => column.table_name && column.column_name)
      }))
      columnCatalog.value = schemas.flatMap((result) => result.status === 'fulfilled' ? result.value : [])
      return columnCatalog.value
    } catch {
      columnCatalog.value = []
      return []
    }
  }

  async function fetchWorkspaces() {
    isLoadingWorkspaces.value = true
    workspaceError.value = ''
    try {
      const response = await workspaceApi.list()
      const nativeItems = (
        response && typeof response === 'object'
          ? (response as { workspaces?: unknown }).workspaces
          : undefined
      )
      const items = (
        Array.isArray(nativeItems)
          ? nativeItems
          : Array.isArray(response)
            ? response
            : []
      ) as WorkspaceRecord[]
      workspaces.value = items
      if (!activeWorkspaceId.value && items.length > 0) {
        const active = items.find((workspace) => workspace.is_active) || items[0]
        activeWorkspaceId.value = String(active.id || '')
      }
      if (activeWorkspaceId.value && !items.some((workspace) => String(workspace.id) === activeWorkspaceId.value)) {
        activeWorkspaceId.value = String(items[0]?.id || '')
        clearWorkspaceDetail()
      }
      if (activeWorkspaceId.value) {
        await Promise.all([
          fetchWorkspaceSummary(activeWorkspaceId.value),
          fetchWorkspaceAIConfig(activeWorkspaceId.value),
        ])
      } else {
        clearWorkspaceDetail()
      }
      return items
    } catch (error) {
      workspaceError.value = error instanceof Error ? error.message : String(error || '')
      throw error
    } finally {
      isLoadingWorkspaces.value = false
    }
  }

  async function createWorkspace(name: unknown, context: unknown = '') {
    return workspaceApi.create(name, context)
  }

  async function activateWorkspace(workspaceId: unknown) {
    const target = String(workspaceId || '').trim()
    if (!target) throw new Error('Select a workspace to activate.')
    await workspaceApi.activate(target)
    activeWorkspaceId.value = target
    workspaces.value = workspaces.value.map((workspace) => ({
      ...workspace,
      is_active: String(workspace.id) === target,
    }))
    clearWorkspaceDetail()
    await Promise.all([fetchWorkspaceSummary(target), fetchWorkspaceAIConfig(target)])
  }

  async function renameWorkspace(workspaceId: unknown, name: unknown, context: unknown = undefined) {
    const target = String(workspaceId || '').trim()
    const updated = await workspaceApi.update(target, name, context) as unknown as WorkspaceRecord
    workspaces.value = workspaces.value.map((workspace) => (
      String(workspace.id) === target ? { ...workspace, ...updated } : workspace
    ))
    if (activeWorkspaceSummary.value && String(activeWorkspaceSummary.value.id) === target) {
      activeWorkspaceSummary.value = { ...activeWorkspaceSummary.value, ...updated }
    }
    return updated
  }

  async function deleteWorkspace(workspaceId: unknown) {
    const target = String(workspaceId || '').trim()
    const result = await workspaceApi.remove(target)
    workspaces.value = workspaces.value.filter((workspace) => String(workspace.id) !== target)
    if (activeWorkspaceId.value === target) {
      activeWorkspaceId.value = ''
      clearWorkspaceDetail()
    }
    return result
  }

  function reset() {
    columnCatalog.value = []
    workspaces.value = []
    activeWorkspaceSummary.value = null
    workspaceAIConfig.value = null
    activeWorkspaceId.value = ''
    workspaceError.value = ''
    isLoadingWorkspaces.value = false
  }

  return {
    columnCatalog,
    workspaces,
    activeWorkspaceSummary,
    workspaceAIConfig,
    activeWorkspaceId,
    schemaContext,
    hasWorkspace,
    isLoadingWorkspaces,
    workspaceError,
    setColumnCatalog,
    setActiveWorkspaceId,
    clearWorkspaceDetail,
    fetchWorkspaceSummary,
    fetchWorkspaceAIConfig,
    saveWorkspaceAIConfig,
    fetchColumnCatalog,
    fetchWorkspaces,
    createWorkspace,
    activateWorkspace,
    renameWorkspace,
    deleteWorkspace,
    reset,
  }
})
