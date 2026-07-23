import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useExecutionStore = defineStore('execution', () => {
  const pythonFileContent = ref('')
  const userEditedCode = ref('')
  const hasUserEditedCode = ref(false)
  const codeEditorSource = ref<'agent' | 'user'>('agent')
  const generatedCode = ref('')
  const conversationRuns = ref<Record<string, unknown>>({})
  const workspaceRuntimeStatusById = ref<Record<string, unknown>>({})
  const terminalOutput = ref('')
  const terminalEntries = ref<unknown[]>([])
  const terminalEntriesTrimmedCount = ref(0)
  const runtimeError = ref('')
  const isCodeRunning = ref(false)
  const backgroundOperations = ref<unknown[]>([])

  return {
    pythonFileContent,
    userEditedCode,
    hasUserEditedCode,
    codeEditorSource,
    generatedCode,
    conversationRuns,
    workspaceRuntimeStatusById,
    terminalOutput,
    terminalEntries,
    terminalEntriesTrimmedCount,
    runtimeError,
    isCodeRunning,
    backgroundOperations,
  }
})
