import { defineStore } from 'pinia'
import { markRaw, ref } from 'vue'

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

  function normalizeOperation(payload: Record<string, unknown> = {}) {
    const now = Date.now()
    return {
      id: String(payload.id || `${payload.type || 'operation'}-${now}-${Math.random().toString(36).slice(2, 8)}`).trim(),
      type: String(payload.type || 'operation').trim(),
      title: String(payload.title || 'Working').trim(),
      message: String(payload.message || '').trim(),
      status: String(payload.status || 'running').trim(),
      progress: Number.isFinite(Number(payload.progress)) ? Math.max(0, Math.min(100, Number(payload.progress))) : null,
      priority: Number.isFinite(Number(payload.priority)) ? Number(payload.priority) : 0,
      createdAt: Number(payload.createdAt || now),
      updatedAt: now,
    }
  }

  function startBackgroundOperation(payload: Record<string, unknown> = {}) {
    const operation = normalizeOperation(payload)
    backgroundOperations.value = [
      ...backgroundOperations.value.filter((item) => String((item as Record<string, unknown>)?.id || '') !== operation.id),
      operation,
    ]
    return operation.id
  }

  function updateBackgroundOperation(operationId: unknown, payload: Record<string, unknown> = {}) {
    const id = String(operationId || '').trim()
    if (!id) return
    backgroundOperations.value = backgroundOperations.value.map((value) => {
      const item = value as Record<string, unknown>
      if (String(item?.id || '') !== id) return item
      return {
        ...item,
        ...payload,
        progress: Number.isFinite(Number(payload.progress))
          ? Math.max(0, Math.min(100, Number(payload.progress)))
          : item.progress,
        updatedAt: Date.now(),
      }
    })
  }

  function finishBackgroundOperation(operationId: unknown, payload: Record<string, unknown> = {}) {
    const id = String(operationId || '').trim()
    if (!id) return
    updateBackgroundOperation(id, {
      ...payload,
      status: String(payload.status || 'complete'),
      progress: Number.isFinite(Number(payload.progress)) ? payload.progress : 100,
    })
    const removeAfterMs = Number(payload.removeAfterMs ?? 3500)
    if (removeAfterMs >= 0) {
      setTimeout(() => {
        backgroundOperations.value = backgroundOperations.value.filter(
          (item) => String((item as Record<string, unknown>)?.id || '') !== id,
        )
      }, removeAfterMs)
    }
  }

  function isConversationRunning(conversationId: unknown) {
    const id = String(conversationId || '').trim()
    const run = conversationRuns.value[id] as Record<string, unknown> | undefined
    return Boolean(id && String(run?.status || '') === 'running')
  }

  function setConversationRun(conversationId: unknown, runState: Record<string, unknown> | null = null) {
    const id = String(conversationId || '').trim()
    if (!id) return
    const next = { ...conversationRuns.value }
    if (!runState) {
      delete next[id]
    } else {
      const current = (next[id] || {}) as Record<string, unknown>
      next[id] = {
        status: String(runState.status || 'running'),
        requestId: String(runState.requestId || current.requestId || ''),
        startedAt: runState.startedAt || current.startedAt || new Date().toISOString(),
        updatedAt: runState.updatedAt || new Date().toISOString(),
        message: String(runState.message || current.message || ''),
        abortController: runState.abortController ? markRaw(runState.abortController) : current.abortController || null,
      }
    }
    conversationRuns.value = next
  }

  function getConversationRun(conversationId: unknown) {
    return (conversationRuns.value[String(conversationId || '').trim()] || null) as Record<string, unknown> | null
  }

  function abortConversationRun(conversationId: unknown) {
    const controller = getConversationRun(conversationId)?.abortController as AbortController | undefined
    if (!controller || typeof controller.abort !== 'function') return false
    controller.abort()
    return true
  }

  function setCodeRunning(running: unknown) {
    isCodeRunning.value = Boolean(running)
    if (running) {
      startBackgroundOperation({
        id: 'code-execution',
        type: 'code',
        title: 'Running code',
        message: 'Executing workspace code...',
        priority: 60,
      })
    } else {
      finishBackgroundOperation('code-execution', {
        title: 'Code run complete',
        message: 'Workspace code execution finished.',
      })
    }
  }

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
    startBackgroundOperation,
    updateBackgroundOperation,
    finishBackgroundOperation,
    isConversationRunning,
    setConversationRun,
    getConversationRun,
    abortConversationRun,
    setCodeRunning,
  }
})
