import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useExecutionStore = defineStore('execution', () => {
  const pythonFileContent = ref('')
  const userEditedCode = ref('')
  const hasUserEditedCode = ref(false)
  const codeEditorSource = ref('agent')
  const historicalCodeBlocks = ref<string[]>([])
  const generatedCode = ref('')
  const terminalOutput = ref('')
  const terminalEntries = ref<unknown[]>([])
  const terminalEntriesTrimmedCount = ref(0)
  const terminalEnabled = ref(false)
  const terminalConsentGranted = ref(false)
  const terminalCwd = ref('')
  const runtimeError = ref('')
  const workspaceRuntimeStatusById = ref<Record<string, unknown>>({})
  const isCodeRunning = ref(false)
  const foregroundOperation = ref<unknown>(null)
  const backgroundOperations = ref<unknown[]>([])

  return {
    pythonFileContent,
    userEditedCode,
    hasUserEditedCode,
    codeEditorSource,
    historicalCodeBlocks,
    generatedCode,
    terminalOutput,
    terminalEntries,
    terminalEntriesTrimmedCount,
    terminalEnabled,
    terminalConsentGranted,
    terminalCwd,
    runtimeError,
    workspaceRuntimeStatusById,
    isCodeRunning,
    foregroundOperation,
    backgroundOperations,
  }
})
