import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import type { WorkspaceSummary } from '../types/workspace'

type WorkspaceRecord = WorkspaceSummary & {
  schema_context?: string
  table_count?: number
}

export const useWorkspaceStore = defineStore('workspaces', () => {
  const columnCatalog = ref<unknown[]>([])
  const workspaces = ref<WorkspaceRecord[]>([])
  const activeWorkspaceSummary = ref<WorkspaceRecord | null>(null)
  const workspaceAIConfig = ref<Record<string, unknown> | null>(null)
  const activeWorkspaceId = ref('')

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

  return {
    columnCatalog,
    workspaces,
    activeWorkspaceSummary,
    workspaceAIConfig,
    activeWorkspaceId,
    schemaContext,
  }
})
