import { defineStore } from 'pinia'
import { computed, markRaw, ref } from 'vue'

const MAX_TERMINAL_ENTRIES = 50
const MAX_TERMINAL_STREAM_CHARS = 200_000
const MAX_TERMINAL_TOTAL_CHARS = 2_000_000
const RUNTIME_STATUSES = new Set(['missing', 'starting', 'ready', 'failed'])

type TerminalEntry = Record<string, unknown> & {
  id: string
  stdout: string
  stderr: string
  status: string
}

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
  const activeBackgroundOperations = computed(() => (
    backgroundOperations.value.filter((value) => {
      const item = value as Record<string, unknown>
      return ['queued', 'running', 'failed', 'complete'].includes(String(item?.status || ''))
    })
  ))
  const primaryBackgroundOperation = computed(() => {
    const running = activeBackgroundOperations.value.filter((value) => {
      const item = value as Record<string, unknown>
      return ['queued', 'running'].includes(String(item?.status || ''))
    })
    const candidates = running.length ? running : activeBackgroundOperations.value
    return candidates
      .slice()
      .sort((leftValue, rightValue) => {
        const left = leftValue as Record<string, unknown>
        const right = rightValue as Record<string, unknown>
        const priorityDelta = Number(right?.priority || 0) - Number(left?.priority || 0)
        return priorityDelta || Number(right?.updatedAt || 0) - Number(left?.updatedAt || 0)
      })[0] || null
  })
  const runningConversationCount = computed(() => (
    Object.values(conversationRuns.value)
      .filter((value) => String((value as Record<string, unknown>)?.status || '') === 'running')
      .length
  ))

  function setPythonFileContent(content: unknown) {
    pythonFileContent.value = String(content || '')
  }

  function setGeneratedCode(code: unknown) {
    const normalized = String(code || '')
    generatedCode.value = normalized
    pythonFileContent.value = normalized
    userEditedCode.value = ''
    hasUserEditedCode.value = false
    codeEditorSource.value = 'agent'
  }

  function setCodeEditorSource(source: unknown) {
    codeEditorSource.value = String(source || '') === 'user' ? 'user' : 'agent'
  }

  function noteUserEditedCode(content: unknown, options: Record<string, unknown> = {}) {
    const normalized = String(content || '')
    pythonFileContent.value = normalized
    userEditedCode.value = normalized
    hasUserEditedCode.value = normalized !== String(options.agentBaseline ?? generatedCode.value)
    codeEditorSource.value = hasUserEditedCode.value ? 'user' : 'agent'
  }

  function setTerminalOutput(output: unknown) {
    terminalOutput.value = String(output || '')
  }

  function setRuntimeError(message: unknown) {
    runtimeError.value = String(message || '')
  }

  function normalizeWorkspaceRuntimeStatus(status: unknown) {
    const normalized = String(status || '').trim().toLowerCase()
    return RUNTIME_STATUSES.has(normalized) ? normalized : 'missing'
  }

  function setWorkspaceRuntimeStatus(workspaceId: unknown, status: unknown) {
    const id = String(workspaceId || '').trim()
    if (!id) return
    workspaceRuntimeStatusById.value = {
      ...workspaceRuntimeStatusById.value,
      [id]: normalizeWorkspaceRuntimeStatus(status),
    }
  }

  function getWorkspaceRuntimeStatus(workspaceId: unknown) {
    const id = String(workspaceId || '').trim()
    if (!id) return 'missing'
    return normalizeWorkspaceRuntimeStatus(workspaceRuntimeStatusById.value[id])
  }

  function trimTerminalStream(value: unknown) {
    const text = String(value || '')
    return text.length > MAX_TERMINAL_STREAM_CHARS
      ? text.slice(text.length - MAX_TERMINAL_STREAM_CHARS)
      : text
  }

  function terminalEntrySize(entry: TerminalEntry) {
    return entry.stdout.length + entry.stderr.length
  }

  function enforceTerminalEntryLimits() {
    let removed = 0
    while (terminalEntries.value.length > MAX_TERMINAL_ENTRIES) {
      terminalEntries.value.shift()
      removed += 1
    }
    let total = terminalEntries.value.reduce<number>(
      (sum, value) => sum + terminalEntrySize(value as TerminalEntry),
      0,
    )
    while (terminalEntries.value.length > 1 && total > MAX_TERMINAL_TOTAL_CHARS) {
      const removedEntry = terminalEntries.value.shift() as TerminalEntry
      total -= terminalEntrySize(removedEntry)
      removed += 1
    }
    terminalEntriesTrimmedCount.value += removed
  }

  function normalizeTerminalEntry(entry: Record<string, unknown>): TerminalEntry {
    const now = Date.now()
    return {
      ...entry,
      id: String(entry.id || `terminal-${now}-${Math.random().toString(36).slice(2, 8)}`),
      stdout: trimTerminalStream(entry.stdout),
      stderr: trimTerminalStream(entry.stderr),
      status: ['queued', 'running', 'complete', 'failed', 'cancelled'].includes(String(entry.status || ''))
        ? String(entry.status)
        : 'complete',
    }
  }

  function appendTerminalEntry(entry: Record<string, unknown> = {}) {
    const normalized = normalizeTerminalEntry(entry)
    terminalEntries.value = [...terminalEntries.value, normalized]
    enforceTerminalEntryLimits()
    return normalized.id
  }

  function updateTerminalEntry(entryId: unknown, patch: Record<string, unknown> = {}) {
    const id = String(entryId || '').trim()
    if (!id) return
    terminalEntries.value = terminalEntries.value.map((value) => {
      const current = value as TerminalEntry
      if (current.id !== id) return current
      return normalizeTerminalEntry({
        ...current,
        ...patch,
        id,
        stdout: Object.prototype.hasOwnProperty.call(patch, 'stdout') ? patch.stdout : current.stdout,
        stderr: Object.prototype.hasOwnProperty.call(patch, 'stderr') ? patch.stderr : current.stderr,
      })
    })
    enforceTerminalEntryLimits()
  }

  function removeTerminalEntry(entryId: unknown) {
    const id = String(entryId || '').trim()
    terminalEntries.value = terminalEntries.value.filter(
      (value) => String((value as TerminalEntry)?.id || '') !== id,
    )
  }

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

  function reset() {
    pythonFileContent.value = ''
    userEditedCode.value = ''
    hasUserEditedCode.value = false
    codeEditorSource.value = 'agent'
    generatedCode.value = ''
    conversationRuns.value = {}
    workspaceRuntimeStatusById.value = {}
    terminalOutput.value = ''
    terminalEntries.value = []
    terminalEntriesTrimmedCount.value = 0
    runtimeError.value = ''
    isCodeRunning.value = false
    backgroundOperations.value = []
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
    activeBackgroundOperations,
    primaryBackgroundOperation,
    runningConversationCount,
    setPythonFileContent,
    setGeneratedCode,
    setCodeEditorSource,
    noteUserEditedCode,
    setTerminalOutput,
    setRuntimeError,
    setWorkspaceRuntimeStatus,
    getWorkspaceRuntimeStatus,
    appendTerminalEntry,
    updateTerminalEntry,
    removeTerminalEntry,
    startBackgroundOperation,
    updateBackgroundOperation,
    finishBackgroundOperation,
    isConversationRunning,
    setConversationRun,
    getConversationRun,
    abortConversationRun,
    setCodeRunning,
    reset,
  }
})
