<template>
  <div class="flex h-full flex-col">
    <Teleport to="#workspace-left-pane-toolbar" v-if="isMounted && appStore.workspacePane === 'code'">
      <div class="flex items-center w-full justify-end">
        <div class="flex items-center gap-1 bg-zinc-50 p-1 rounded-xl border border-zinc-200">
          <button
            @click="runCode"
            :disabled="!canRunCode || isRunning"
            title="Run Code (R)"
            class="btn-icon"
            :class="canRunCode && !isRunning
              ? 'hover:bg-white hover:text-green-600 hover:shadow-sm'
              : ''"
          >
            <PlayIcon v-if="!isRunning" class="h-4 w-4" />
            <div v-else class="h-4 w-4 animate-spin rounded-full border-b-2 border-gray-400"></div>
          </button>

          <button
            @click="syncTableNameInCode"
            title="Sync table name in code to current data file"
            class="btn-icon hover:bg-white hover:text-blue-600 hover:shadow-sm"
          >
            <ArrowPathIcon class="h-4 w-4" />
          </button>

          <div class="w-px h-4 bg-zinc-200 mx-0.5"></div>

          <button
            @click="undo"
            :disabled="!canUndo"
            class="btn-icon"
            :class="canUndo ? 'hover:bg-white hover:text-blue-600 hover:shadow-sm' : ''"
            title="Undo (Ctrl+Z)"
          >
            <ArrowUturnLeftIcon class="h-4 w-4" />
          </button>

          <button
            @click="redo"
            :disabled="!canRedo"
            class="btn-icon"
            :class="canRedo ? 'hover:bg-white hover:text-blue-600 hover:shadow-sm' : ''"
            title="Redo (Ctrl+Y)"
          >
            <ArrowUturnRightIcon class="h-4 w-4" />
          </button>
          
          <div class="w-px h-4 bg-zinc-200 mx-0.5"></div>

          <button
            @click="downloadCode"
            :disabled="!appStore.pythonFileContent"
            class="btn-icon"
            :class="appStore.pythonFileContent ? 'hover:bg-white hover:text-blue-600 hover:shadow-sm' : ''"
            title="Download code"
          >
            <ArrowDownTrayIcon class="h-4 w-4" />
          </button>
        </div>
      </div>
    </Teleport>

    <div class="relative flex-1" style="min-height: 400px;">
      <div ref="editorContainer" class="h-full w-full" style="min-height: 400px; position: relative; z-index: 1;"></div>

      <div
        v-if="isGeneratingCode"
        class="absolute inset-0 z-10 flex items-center justify-center bg-white bg-opacity-90"
      >
        <div class="text-center">
          <div class="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-b-2 border-blue-600"></div>
          <p class="text-sm font-medium text-gray-900">Generating code...</p>
          <p class="mt-1 text-xs text-gray-500">AI is creating Python code for your analysis</p>
        </div>
      </div>

      <div
        v-if="!appStore.pythonFileContent.trim() && !isGeneratingCode"
        class="pointer-events-none absolute inset-0 flex items-center justify-center"
      >
        <div class="text-center text-gray-400">
          <CodeBracketIcon class="mx-auto mb-2 h-10 w-10" />
          <p class="text-sm text-gray-500">Start writing your Python code</p>
          <p class="mt-1 text-xs text-gray-400">One file per session - your code is automatically saved</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useAppStore } from '../../stores/appStore'
import { useAuthStore } from '../../stores/authStore'
import apiService from '../../services/apiService'
import executionService from '../../services/executionService'
import { toast } from '../../composables/useToast'
import { buildExecutionViewModel } from '../../utils/executionViewModel'
import { normalizeExecutionResponse } from '../../utils/runtimeExecution'
import {
  decideExecutionTabWithSelection,
  prioritizeByName,
  resolvePreferredArtifactNames,
} from '../../utils/executionRouting'

import { EditorView, basicSetup } from 'codemirror'
import { EditorState, Prec } from '@codemirror/state'
import { python } from '@codemirror/lang-python'
import { autocompletion } from '@codemirror/autocomplete'
import { keymap } from '@codemirror/view'
import { searchKeymap } from '@codemirror/search'
import { toggleComment, indentMore, indentLess } from '@codemirror/commands'
import { indentUnit } from '@codemirror/language'

import {
  PlayIcon,
  ArrowPathIcon,
  ArrowDownTrayIcon,
  ArrowUturnLeftIcon,
  ArrowUturnRightIcon,
  CodeBracketIcon,
} from '@heroicons/vue/24/outline'

const appStore = useAppStore()
const authStore = useAuthStore()

const editorContainer = ref(null)
const isRunning = ref(false)
const isGeneratingCode = ref(false)
const databasePaths = ref(null)
const settingsInfo = ref(null)
const isMounted = ref(false)
let lastRunBlockedToastAt = 0

let editor = null
let isUpdatingFromStore = false

const hasSelectedData = computed(() => {
  const selectedPath = String(appStore.dataFilePath || '').trim()
  const selectedTable = String(appStore.ingestedTableName || '').trim()
  return Boolean(selectedPath || selectedTable)
})

function applyExecutionArtifactsToStore(viewModel) {
  appStore.setDataframes(viewModel.dataframes)
  if (viewModel.dataframes.length > 0) {
    appStore.setResultData(viewModel.dataframes[0].data)
  }

  appStore.setFigures(viewModel.figures)
  if (viewModel.figures.length > 0) {
    appStore.setPlotlyFigure(viewModel.figures[0].data)
  }
}

async function fetchDatabasePaths() {
  try {
    databasePaths.value = await apiService.getDatabasePaths()
  } catch (_error) {
    databasePaths.value = null
  }
}

async function fetchSettings() {
  try {
    settingsInfo.value = await apiService.getSettings()
  } catch (_error) {
    settingsInfo.value = null
  }
}

function getTableName(path) {
  const cleaned = String(path || '').trim()
  if (!cleaned) return 'your_table'
  const parts = cleaned.split(/[\\/]/)
  const filename = parts[parts.length - 1] || 'your_table'
  const withoutExt = filename.replace(/\.[^.]+$/, '')
  return withoutExt.replace(/[^a-zA-Z0-9_]/g, '_').toLowerCase() || 'your_table'
}

const defaultCodeTemplate = computed(() => {
  const originalFilepath = appStore.dataFilePath || '/path/to/your/data/file.csv'
  const dbPath = databasePaths.value?.database_path
  const backendTable = settingsInfo.value?.table_name || settingsInfo.value?.data_table_name || settingsInfo.value?.table || null
  const tableName = backendTable || getTableName(originalFilepath)

  return `import duckdb

table_name = "${tableName}"
limit_rows = 100

def quote_ident(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'

quoted_table = quote_ident(table_name)

try:
    conn  # type: ignore  # noqa
except NameError:
    conn = duckdb.connect(r"${dbPath || ''}") if "${dbPath || ''}".strip() else duckdb.connect()

head_100 = conn.sql(f"SELECT * FROM {quoted_table} LIMIT {limit_rows}").df()
tail_100 = conn.sql(
    f"""
    WITH numbered AS (
      SELECT *, row_number() OVER () AS __rownum
      FROM {quoted_table}
    )
    SELECT * EXCLUDE (__rownum)
    FROM numbered
    ORDER BY __rownum DESC
    LIMIT {limit_rows}
    """
).df()
sample_100 = conn.sql(f"SELECT * FROM {quoted_table} USING SAMPLE {limit_rows} ROWS").df()

combined_preview = conn.sql(
    f"""
    SELECT 'head' AS sample_bucket, * FROM (
      SELECT * FROM {quoted_table} LIMIT {limit_rows}
    )
    UNION ALL
    SELECT 'tail' AS sample_bucket, * FROM (
      WITH numbered AS (
        SELECT *, row_number() OVER () AS __rownum
        FROM {quoted_table}
      )
      SELECT * EXCLUDE (__rownum)
      FROM numbered
      ORDER BY __rownum DESC
      LIMIT {limit_rows}
    )
    UNION ALL
    SELECT 'sample' AS sample_bucket, * FROM (
      SELECT * FROM {quoted_table} USING SAMPLE {limit_rows} ROWS
    )
    """
).df()

combined_preview
`
})

function replaceTableNameInCode(src, newName) {
  if (!src || !newName) return src
  const re = /(\n|^)\s*table_name\s*=\s*(["'])(.*?)\2/g
  return src.replace(re, (m, p1, quote) => `${p1}table_name = ${quote}${newName}${quote}`)
}

async function syncTableNameInCode(silent = false) {
  if (!hasSelectedData.value) {
    if (!silent) toast.info('Select a dataset first')
    return
  }
  await fetchSettings()
  const backendTable = settingsInfo.value?.table_name || settingsInfo.value?.data_table_name || settingsInfo.value?.table || null
  const tableName = backendTable || getTableName(appStore.dataFilePath || '')

  const current = appStore.pythonFileContent
  const updated = replaceTableNameInCode(current, tableName)
  if (updated !== current) {
    appStore.setPythonFileContent(updated)
    updateEditorContent()
    if (!silent) toast.success('Synced table name in code')
  } else if (isDefaultEditorContent(current.trim())) {
    appStore.setPythonFileContent(defaultCodeTemplate.value)
    updateEditorContent()
    if (!silent) toast.success('Refreshed code template with new table name')
  } else if (!silent) {
    toast.info('No table_name assignment found to update')
  }
}

const canRunCode = computed(() => appStore.pythonFileContent.trim() && !isRunning.value && !appStore.isCodeRunning)
const canUndo = computed(() => editor && editor.state && editor.state.undoDepth > 0)
const canRedo = computed(() => editor && editor.state && editor.state.redoDepth > 0)

function executionInProgress() {
  return isRunning.value || appStore.isCodeRunning
}

function notifyExecutionInProgress() {
  const now = Date.now()
  if (now - lastRunBlockedToastAt < 1500) return
  lastRunBlockedToastAt = now
  toast.warning('Execution in progress', 'Please wait for the current run to finish.')
}

function getSelectedSnippet() {
  if (!editor || !editor.state) return ''
  const snippets = editor.state.selection.ranges
    .map((range) => {
      if (!range.empty) {
        return editor.state.doc.sliceString(range.from, range.to)
      }
      const line = editor.state.doc.lineAt(range.head)
      return line?.text || ''
    })
    .filter((text) => text && text.trim())
  return snippets.join('\n\n')
}

function createRunId() {
  const ts = Date.now().toString(36)
  const rand = Math.random().toString(36).slice(2, 7)
  return `run_${ts}_${rand}`
}

function startRunEntry(scopeLabel) {
  const runId = createRunId()
  const entryId = appStore.appendTerminalEntry({
    kind: 'output',
    source: 'analysis',
    label: scopeLabel,
    runId,
    status: 'running',
    stdout: '',
    stderr: '',
    exitCode: 0,
  })
  return {
    entryId,
    runId,
    startedAtMs: performance.now(),
  }
}

async function executeSnippet(code, successLine, options = {}) {
  const preferOutputPane = options?.preferOutputPane === true
  const preserveActiveTabOnNoOutput = options?.preserveActiveTabOnNoOutput === true
  const runEntryId = String(options?.runEntryId || '').trim()
  const runId = String(options?.runId || '').trim()
  const start = performance.now()
  const pyResponse = await executionService.executePython(code)
  const execTime = (performance.now() - start) / 1000
  const normalized = normalizeExecutionResponse({
    success: pyResponse.success,
    stdout: pyResponse.stdout,
    stderr: pyResponse.stderr,
    has_stdout: pyResponse.hasStdout,
    has_stderr: pyResponse.hasStderr,
    error: pyResponse.error,
    result: pyResponse.result,
    result_type: pyResponse.resultType,
    result_kind: pyResponse.resultKind,
    result_name: pyResponse.resultName,
    variables: pyResponse.variables,
  })

  const viewModel = buildExecutionViewModel(
    {
      ...normalized,
      execution_time: execTime,
    },
    {
      successLine,
      includeVariableSummary: true,
    },
  )

  const outputStdout = String(normalized?.stdout || '')
  const outputStderr = String(normalized?.stderr || normalized?.error || '')
  const status = normalized?.error ? 'error' : 'success'
  const runEntryPayload = {
    kind: 'output',
    source: 'analysis',
    label: 'Run output',
    runId,
    status,
    stdout: outputStdout,
    stderr: outputStderr,
    exitCode: normalized?.error ? 1 : 0,
    durationMs: Math.round(execTime * 1000),
  }
  if (runEntryId) {
    appStore.updateTerminalEntry(runEntryId, runEntryPayload)
  } else {
    appStore.appendTerminalEntry({
      kind: 'output',
      source: 'analysis',
      ...runEntryPayload,
    })
  }

  if (normalized?.error) {
    appStore.setTerminalOutput(viewModel.output)
    appStore.setActiveTab('output')
    return {
      ok: false,
      execTime,
      hasDataframes: false,
      hasFigures: false,
      hasConsoleOutput: Boolean(outputStdout || outputStderr),
    }
  }

  const preferred = resolvePreferredArtifactNames(viewModel, normalized)
  const orderedViewModel = {
    ...viewModel,
    dataframes: prioritizeByName(viewModel.dataframes, preferred.dataframeName),
    figures: prioritizeByName(viewModel.figures, preferred.figureName),
  }
  const hasArtifacts = orderedViewModel.dataframes.length > 0 || orderedViewModel.figures.length > 0
  const hasConsoleOutput = Boolean(outputStdout || outputStderr)

  applyExecutionArtifactsToStore(orderedViewModel)
  const targetTab = decideExecutionTabWithSelection({
    resultType: normalized?.result_type,
    resultKind: normalized?.result_kind,
    resultName: normalized?.result_name,
    hasError: false,
    hasDataframes: orderedViewModel.dataframes.length > 0,
    hasFigures: orderedViewModel.figures.length > 0,
    selectedCode: code,
    dataframeNames: orderedViewModel.dataframes.map((df) => String(df?.name || '')),
    figureNames: orderedViewModel.figures.map((fig) => String(fig?.name || '')),
  })
  if (preferOutputPane) {
    appStore.setActiveTab('output')
  } else if (targetTab) {
    appStore.setActiveTab(targetTab)
  } else if (hasConsoleOutput) {
    appStore.setActiveTab('output')
  } else if (preserveActiveTabOnNoOutput) {
    // Selection-style no-op execution (e.g. assignment only): keep current pane.
  } else {
    appStore.setActiveTab('output')
  }
  if (!preserveActiveTabOnNoOutput || hasArtifacts || hasConsoleOutput) {
    appStore.setTerminalOutput(viewModel.output)
  }
  return {
    ok: true,
    execTime,
    hasDataframes: orderedViewModel.dataframes.length > 0,
    hasFigures: orderedViewModel.figures.length > 0,
    hasConsoleOutput: Boolean(outputStdout || outputStderr),
  }
}

async function runCode() {
  if (!canRunCode.value) {
    if (executionInProgress()) notifyExecutionInProgress()
    return
  }
  isRunning.value = true
  appStore.setCodeRunning(true)
  appStore.setActiveTab('output')
  appStore.setTerminalOutput('Running code...')
  const runMeta = startRunEntry('Code run')
  try {
    await executeSnippet(appStore.pythonFileContent, 'Code executed successfully!', {
      runEntryId: runMeta.entryId,
      runId: runMeta.runId,
    })
  } catch (error) {
    const errorMessage = error.response?.data?.detail || error.message || 'Code execution failed'
    appStore.setTerminalOutput(`Error: ${errorMessage}`)
    appStore.updateTerminalEntry(runMeta.entryId, {
      status: 'error',
      runId: runMeta.runId,
      stdout: '',
      stderr: errorMessage,
      exitCode: 1,
      durationMs: Math.round(performance.now() - runMeta.startedAtMs),
    })
  } finally {
    isRunning.value = false
    appStore.setCodeRunning(false)
  }
}

async function runSelectedCode() {
  if (executionInProgress()) {
    notifyExecutionInProgress()
    return
  }
  const selectedCode = getSelectedSnippet()
  if (!selectedCode) {
    toast.info('No selected code or non-empty current line to run.')
    return
  }

  isRunning.value = true
  appStore.setCodeRunning(true)
  const runMeta = startRunEntry('Selection run')

  try {
    await executeSnippet(
      selectedCode,
      'Selected code executed successfully!',
      {
        preserveActiveTabOnNoOutput: true,
        runEntryId: runMeta.entryId,
        runId: runMeta.runId,
      },
    )
  } catch (error) {
    const errorMessage = error.response?.data?.detail || error.message || 'Code execution failed'
    appStore.setTerminalOutput(`Error: ${errorMessage}`)
    appStore.updateTerminalEntry(runMeta.entryId, {
      status: 'error',
      runId: runMeta.runId,
      stdout: '',
      stderr: errorMessage,
      exitCode: 1,
      durationMs: Math.round(performance.now() - runMeta.startedAtMs),
    })
  } finally {
    isRunning.value = false
    appStore.setCodeRunning(false)
  }
}

const customKeymap = [
  ...searchKeymap,
  { key: 'Tab', run: indentMore },
  { key: 'Shift-Tab', run: indentLess },
  { key: 'Mod-/', run: toggleComment },
  {
    key: 'Mod-Enter',
    run: () => {
      if (canRunCode.value) {
        runCode()
        return true
      }
      return false
    },
  },
  {
    key: 'Shift-Enter',
    run: () => {
      runSelectedCode()
      return true
    },
  },
  {
    key: 'Mod-r',
    run: () => {
      if (canRunCode.value) {
        runCode()
        return true
      }
      return false
    },
  },
]

function updateEditorContent() {
  if (editor && !isUpdatingFromStore) {
    const content = appStore.pythonFileContent
    const currentContent = editor.state.doc.toString()
    if (currentContent !== content) {
      isUpdatingFromStore = true
      const transaction = editor.state.update({
        changes: {
          from: 0,
          to: editor.state.doc.length,
          insert: content,
        },
      })
      editor.dispatch(transaction)
      setTimeout(() => {
        isUpdatingFromStore = false
      }, 10)
    }
  }
}

async function initializeEditor() {
  if (!editorContainer.value) return

  const extensions = [
    basicSetup,
    indentUnit.of('    '),
    python(),
    autocompletion(),
    Prec.highest(keymap.of(customKeymap)),
    EditorView.theme({
      '&': { fontSize: '14px', height: '100%', backgroundColor: '#FDFCF8' },
      '.cm-editor': { backgroundColor: '#FDFCF8' },
      '.cm-scroller': { fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace', backgroundColor: '#FDFCF8' },
      '.cm-gutters': { backgroundColor: '#F5F3ED', borderRight: '1px solid #E8E4DC', color: '#8a8070' },
      '.cm-content': { padding: '16px' },
      '.cm-focused': { outline: 'none' },
    }),
    EditorView.updateListener.of((update) => {
      // Handle content changes
      if (update.docChanged && !isUpdatingFromStore) {
        const content = editor.state.doc.toString()
        isUpdatingFromStore = true
        appStore.setPythonFileContent(content)
        setTimeout(() => {
          isUpdatingFromStore = false
        }, 10)
      }

      // Handle cursor position updates
      if (update.selectionSet || update.docChanged) {
        const head = update.state.selection.main.head
        const line = update.state.doc.lineAt(head)
        appStore.setEditorPosition(line.number, head - line.from + 1)
      }
    }),
    EditorView.domEventHandlers({
      focus: () => {
        appStore.setEditorFocused(true)
        // Ensure accurate position on initial focus
        if (editor) {
          const head = editor.state.selection.main.head
          const line = editor.state.doc.lineAt(head)
          appStore.setEditorPosition(line.number, head - line.from + 1)
        }
      },
      blur: () => {
        appStore.setEditorFocused(false)
      }
    }),
    EditorView.lineWrapping,
  ]

  const state = EditorState.create({
    doc: appStore.pythonFileContent,
    extensions,
  })

  editor = new EditorView({
    state,
    parent: editorContainer.value,
  })
}

function downloadCode() {
  try {
    const code = appStore.pythonFileContent || '# No code in editor'
    const blob = new Blob([code], { type: 'text/plain' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-')
    link.download = `python_code_${timestamp}.py`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Failed to download code:', error)
  }
}

function undo() {
  if (editor && canUndo.value) editor.dispatch(editor.state.undo())
}

function redo() {
  if (editor && canRedo.value) editor.dispatch(editor.state.redo())
}

function isDefaultEditorContent(content) {
  const current = (content || '').trim()
  return current === '' || current === '# Python code for data analysis'
}

onMounted(async () => {
  isMounted.value = true
  await nextTick()
  await fetchSettings()
  await fetchDatabasePaths()

  await initializeEditor()
})

onUnmounted(() => {
  if (editor) editor.destroy()
})

watch(() => appStore.generatedCode, (newCode) => {
  if (newCode) {
    appStore.setPythonFileContent(newCode)
    updateEditorContent()
    isGeneratingCode.value = false
    appStore.setLoading(false)
    appStore.setCodeRunning(false)  }
})

watch(() => appStore.isLoading, (loading) => {
  isGeneratingCode.value = loading
})

watch(() => appStore.pythonFileContent, () => {
  if (!isUpdatingFromStore && editor) {
    updateEditorContent()
  }
})

watch(() => authStore.userId, async (newUserId, oldUserId) => {
  if (newUserId !== oldUserId && newUserId) {
    await fetchDatabasePaths()
  }
})
</script>

<style scoped>
/* CodeMirror styling is handled by editor theme extension */
:deep(.cm-content) {
  min-width: 40ch;
}
:deep(.cm-scroller) {
  overflow-x: auto !important;
}
</style>
