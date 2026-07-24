import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useWorkspaceStore = defineStore('workspace', () => {
  const dataFilePath = ref('')
  const schemaFilePath = ref('')
  const schemaFileId = ref('')
  const isSchemaFileUploaded = ref(false)
  const ingestedTableName = ref('')
  const ingestedColumns = ref<unknown[]>([])
  const columnCatalog = ref<unknown[]>([])
  const profileData = ref<unknown>(null)
  const schemaContext = ref('')
  const allowSchemaSampleValues = ref(false)
  const allowLlmDataSamples = ref(false)
  const workspaces = ref<unknown[]>([])
  const activeWorkspaceSummary = ref<unknown>(null)
  const workspaceAIConfig = ref<unknown>(null)
  const workspaceAIConfigLoading = ref(false)
  const workspaceDeletionJobs = ref<unknown[]>([])
  const activeWorkspaceId = ref('')

  return {
    dataFilePath,
    schemaFilePath,
    schemaFileId,
    isSchemaFileUploaded,
    ingestedTableName,
    ingestedColumns,
    columnCatalog,
    profileData,
    schemaContext,
    allowSchemaSampleValues,
    allowLlmDataSamples,
    workspaces,
    activeWorkspaceSummary,
    workspaceAIConfig,
    workspaceAIConfigLoading,
    workspaceDeletionJobs,
    activeWorkspaceId,
  }
})
