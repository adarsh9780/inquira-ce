<template>
  <div class="flex h-full flex-col">
    <Teleport to="#workspace-left-pane-toolbar" v-if="isMounted && uiStore.workspacePane === 'code'">
      <div class="flex items-center w-full justify-between gap-2">
        <div v-if="showCodeSourceToggle" class="flex items-center gap-1">
          <button
            type="button"
            class="rounded-md px-2.5 py-1 text-xs font-medium leading-4 transition-colors"
            :style="codeSourceButtonStyle('agent')"
            :aria-pressed="appStore.codeEditorSource === 'agent'"
            title="Use agent generated code"
            @click="selectCodeSource('agent')"
          >
            Generated code
          </button>
          <button
            type="button"
            class="rounded-md px-2.5 py-1 text-xs font-medium leading-4 transition-colors"
            :style="codeSourceButtonStyle('user')"
            :aria-pressed="appStore.codeEditorSource === 'user'"
            title="Use your edited code"
            @click="selectCodeSource('user')"
          >
            My edits
          </button>
          <span v-if="hasDistinctUserRevision" class="ml-1 text-[11px] font-medium text-[var(--color-accent-text)]">
            Modified
          </span>
        </div>
        <div v-else></div>
        <div class="flex items-center gap-1">
          <button
            @click="runCode"
            :disabled="!canRunCode || isRunning"
            title="Run Code (R)"
            class="btn-primary h-8 gap-1.5 px-3 text-xs"
            data-code-run
          >
            <PlayIcon v-if="!isRunning" class="h-4 w-4" />
            <div
              v-else
              class="h-4 w-4 animate-spin rounded-full border-2"
              style="border-color: color-mix(in srgb, var(--color-on-accent) 35%, transparent); border-top-color: var(--color-on-accent);"
            ></div>
            <span>{{ isRunning ? 'Running…' : 'Run' }}</span>
          </button>

          <button
            @click="syncTableNameInCode"
            title="Sync table name in code to the active workspace"
            class="btn-icon"
          >
            <ArrowPathIcon class="h-4 w-4" />
          </button>

          <div class="mx-0.5 h-4 w-px bg-[var(--color-border)]"></div>

          <button
            @click="undo"
            :disabled="!canUndo"
            class="btn-icon"
            title="Undo (Ctrl+Z)"
          >
            <ArrowUturnLeftIcon class="h-4 w-4" />
          </button>

          <button
            @click="redo"
            :disabled="!canRedo"
            class="btn-icon"
            title="Redo (Ctrl+Y)"
          >
            <ArrowUturnRightIcon class="h-4 w-4" />
          </button>

          <div class="mx-0.5 h-4 w-px bg-[var(--color-border)]"></div>

          <button
            @click="downloadCode"
            :disabled="!appStore.pythonFileContent"
            class="btn-icon"
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
        class="pointer-events-none absolute right-3 top-3 z-10"
      >
        <div
          class="flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium shadow-sm"
          style="background-color: color-mix(in srgb, var(--color-surface) 92%, var(--color-base)); border-color: var(--color-border); color: var(--color-text-main);"
        >
          <div class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-[var(--color-border)] border-t-[var(--color-accent)]"></div>
          <span>Generating code...</span>
        </div>
      </div>

      <div
        v-if="!appStore.pythonFileContent.trim() && !isGeneratingCode"
        class="pointer-events-none absolute inset-0 flex items-center justify-center"
      >
        <div class="text-center text-[var(--color-text-muted)]">
          <CodeBracketIcon class="mx-auto mb-2 h-10 w-10" />
          <p class="text-sm text-[var(--color-text-main)]">Start writing your Python code</p>
          <p class="mt-1 text-xs text-[var(--color-text-muted)]">One file per session - your code is automatically saved</p>
          <p class="mt-2 max-w-md text-xs text-[var(--color-warning-text)]">
            Python runs locally with your user permissions and is not sandboxed. Review code before running it.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useAppStore } from '../../stores/appStore'
import { useUiStore } from '../../stores/uiStore'
import executionService from '../../services/executionService'
import { toast } from '../../composables/useToast'
import { buildExecutionViewModel } from '../../utils/executionViewModel'
import { latestExpressionVariables, normalizeExecutionResponse } from '../../utils/runtimeExecution'
import { persistExportFile } from '../../utils/exportFile'

import { EditorView, basicSetup } from 'codemirror'
import { Compartment, EditorState, Prec } from '@codemirror/state'
import { python } from '@codemirror/lang-python'
import { autocompletion, acceptCompletion, completionStatus } from '@codemirror/autocomplete'
import { keymap } from '@codemirror/view'
import { searchKeymap } from '@codemirror/search'
import { toggleComment, indentMore, indentLess, insertNewlineAndIndent } from '@codemirror/commands'
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
const uiStore = useUiStore()

const editorContainer = ref(null)
const isRunning = ref(false)
const isGeneratingCode = ref(false)
const isMounted = ref(false)
let lastRunBlockedToastAt = 0

let editor = null
let isUpdatingFromStore = false
const editableCompartment = new Compartment()
const visualThemeCompartment = new Compartment()

const primaryWorkspaceTableName = computed(() => {
  const summaryTable = (Array.isArray(appStore.activeWorkspaceSummary?.table_names)
    ? appStore.activeWorkspaceSummary.table_names
    : []
  ).map((name) => String(name || '').trim()).find(Boolean)
  if (summaryTable) return summaryTable
  const catalogItem = (Array.isArray(appStore.columnCatalog) ? appStore.columnCatalog : [])
    .find((item) => String(item?.table_name || '').trim())
  return String(catalogItem?.table_name || '').trim()
})

const hasSelectedData = computed(() => {
  return Number(appStore.activeWorkspaceSummary?.table_count || 0) > 0
    || Boolean(primaryWorkspaceTableName.value)
})

function isSimpleIdentifier(value) {
  return /^[A-Za-z_][A-Za-z0-9_]*$/.test(String(value || '').trim())
}

function quoteSqlIdentifier(value) {
  return `"${String(value || '').replace(/"/g, '""')}"`
}

function buildColumnReference(tableName, columnName) {
  const table = String(tableName || '').trim()
  const column = String(columnName || '').trim()
  if (!table || !column) return ''
  if (isSimpleIdentifier(column)) return `${table}.${column}`
  return `${table}.${quoteSqlIdentifier(column)}`
}

function buildColumnCompletionOptions(query = '') {
  const loweredQuery = String(query || '').toLowerCase()
  const options = []
  const seen = new Set()
  const addOption = ({ tableName, columnName, dtype = '' }) => {
    const safeTable = String(tableName || '').trim()
    const safeColumn = String(columnName || '').trim()
    const safeDtype = String(dtype || '').trim()
    if (!safeTable || !safeColumn) return

    if (!seen.has(safeTable)) {
      const tableLower = safeTable.toLowerCase()
      if (!loweredQuery || tableLower.includes(loweredQuery) || `${tableLower}.`.startsWith(loweredQuery)) {
        options.push({
          label: safeTable,
          type: 'keyword',
          detail: 'table',
        })
      }
      seen.add(safeTable)
    }

    const fullColumn = buildColumnReference(safeTable, safeColumn)
    const dotColumn = `${safeTable}.${safeColumn}`
    if (seen.has(fullColumn)) return
    const searchPool = [fullColumn, dotColumn, safeTable, safeColumn].map((entry) => entry.toLowerCase())
    if (!loweredQuery || searchPool.some((entry) => entry.includes(loweredQuery) || entry.startsWith(loweredQuery))) {
      options.push({
        label: fullColumn,
        type: 'variable',
        detail: safeDtype || (isSimpleIdentifier(safeColumn) ? 'column' : 'column (quoted)'),
      })
    }
    seen.add(fullColumn)
  }

  const columns = Array.isArray(appStore.columnCatalog) ? appStore.columnCatalog : []

  columns.forEach((item) => {
    addOption({
      tableName: item?.table_name,
      columnName: item?.column_name,
      dtype: item?.dtype,
    })
  })

  return options.slice(0, 120)
}

function completionSource(context) {
  const word = context.matchBefore(/[A-Za-z_][\w.\[\]"']*/)
  if (!word) {
    if (!context.explicit) return null
    const options = buildColumnCompletionOptions('')
    if (!options.length) return null
    return {
      from: context.pos,
      options,
      validFor: /^[A-Za-z_][\w.\[\]"']*$/,
    }
  }
  if (word.from === word.to && !context.explicit) return null

  const options = buildColumnCompletionOptions(word.text)
  if (!options.length) return null

  return {
    from: word.from,
    options,
    validFor: /^[A-Za-z_][\w.\[\]"']*$/,
  }
}

function stampRunResults(items, runId, createdAt) {
  return (Array.isArray(items) ? items : []).map((item) => ({
    ...item,
    runId,
    origin: 'user',
    createdAt: item?.createdAt || item?.created_at || createdAt,
  }))
}

const defaultCodeTemplate = computed(() => {
  const tableName = primaryWorkspaceTableName.value || 'your_table'

  return `import duckdb

table_name = "${tableName}"
limit_rows = 100

def quote_ident(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'

quoted_table = quote_ident(table_name)

try:
    conn  # type: ignore  # noqa
except NameError:
    raise RuntimeError("Workspace runtime connection is not ready. Wait for the workspace to be ready, then run this code again.")

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
  const tableName = primaryWorkspaceTableName.value

  const current = appStore.pythonFileContent
  const updated = replaceTableNameInCode(current, tableName)
  if (updated !== current) {
    appStore.noteUserEditedCode(updated, { baselineCode: current })
    updateEditorContent()
    if (!silent) toast.success('Synced table name in code')
  } else if (isDefaultEditorContent(current.trim())) {
    appStore.noteUserEditedCode(defaultCodeTemplate.value, { baselineCode: current })
    updateEditorContent()
    if (!silent) toast.success('Refreshed code template with new table name')
  } else if (!silent) {
    toast.info('No table_name assignment found to update')
  }
}

const canRunCode = computed(() => appStore.pythonFileContent.trim() && !isRunning.value && !appStore.isCodeRunning)
const canUndo = computed(() => editor && editor.state && editor.state.undoDepth > 0)
const canRedo = computed(() => editor && editor.state && editor.state.redoDepth > 0)
const showCodeSourceToggle = computed(() => {
  const generated = String(appStore.generatedCode || appStore.activeTurnCode || '')
  const edited = String(appStore.userEditedCode || appStore.pythonFileContent || '')
  return Boolean(generated && appStore.hasUserEditedCode && edited !== generated)
})

function codeSourceButtonStyle(source) {
  const active = appStore.codeEditorSource === source
  if (active) {
    return {
      backgroundColor: 'var(--color-surface)',
      color: 'var(--color-text-main)',
      borderColor: 'color-mix(in srgb, var(--color-border) 80%, transparent)',
    }
  }
  return {
    backgroundColor: 'transparent',
    color: 'var(--color-text-muted)',
    borderColor: 'transparent',
  }
}

function selectCodeSource(source) {
  if (source === appStore.codeEditorSource) return
  appStore.setCodeEditorSource(source)
}

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

function startRunEntry(scopeLabel, code) {
  const runId = createRunId()
  const entryId = appStore.appendTerminalEntry({
    kind: 'output',
    source: 'analysis',
    origin: 'user',
    conversationId: String(appStore.activeConversationId || ''),
    label: scopeLabel,
    command: String(code || ''),
    runId,
    status: 'running',
    stdout: '',
    stderr: '',
    exitCode: 0,
  })
  if (entryId) {
    uiStore.setDataPane('output')
  }
  return {
    entryId,
    runId,
    startedAtMs: performance.now(),
  }
}

async function executeSnippet(code, successLine, options = {}) {
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
    run_id: pyResponse.runId,
    artifacts: pyResponse.artifacts,
    variables: pyResponse.variables,
  })

  const viewModel = buildExecutionViewModel(
    {
      ...normalized,
      // A notebook cell displays only its final expression. Kernel variables and
      // exports remain available to later code but are not repeated as outputs.
      variables: latestExpressionVariables(normalized),
      artifacts: normalized.artifacts,
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
  const effectiveRunId = String(normalized?.run_id || runId || '')
  const runEntryPayload = {
    kind: 'output',
    source: 'analysis',
    origin: 'user',
    conversationId: String(appStore.activeConversationId || ''),
    runId: effectiveRunId,
    status,
    stdout: outputStdout,
    stderr: outputStderr,
    exitCode: normalized?.error ? 1 : 0,
    durationMs: Math.round(execTime * 1000),
    hasTableOutput: false,
    hasChartOutput: false,
    scalarOutputs: [],
    tableOutputs: [],
    chartOutputs: [],
  }
  let effectiveRunEntryId = runEntryId
  if (runEntryId) {
    appStore.updateTerminalEntry(runEntryId, runEntryPayload)
  } else {
    effectiveRunEntryId = appStore.appendTerminalEntry({
      kind: 'output',
      source: 'analysis',
      label: 'Code run',
      command: String(code || ''),
      ...runEntryPayload,
    })
  }

  if (normalized?.error) {
    appStore.setTerminalOutput(viewModel.output)
    uiStore.setDataPane('output')
    return {
      ok: false,
      execTime,
      hasDataframes: false,
      hasFigures: false,
      hasConsoleOutput: Boolean(outputStdout || outputStderr),
    }
  }

  const hasConsoleOutput = Boolean(outputStdout || outputStderr)

  const createdAt = new Date().toISOString()
  const tableOutputs = stampRunResults(viewModel.dataframes.slice(0, 1), effectiveRunId, createdAt)
  const chartOutputs = stampRunResults(viewModel.figures.slice(0, 1), effectiveRunId, createdAt)
  const scalarOutputs = stampRunResults(viewModel.scalars.slice(0, 1), effectiveRunId, createdAt)
  if (effectiveRunEntryId) {
    appStore.updateTerminalEntry(effectiveRunEntryId, {
      hasTableOutput: tableOutputs.length > 0,
      hasChartOutput: chartOutputs.length > 0,
      tableOutputs,
      chartOutputs,
      scalarOutputs,
    })
  }
  uiStore.setDataPane('output')
  appStore.setTerminalOutput(viewModel.output)
  return {
    ok: true,
    execTime,
    hasDataframes: tableOutputs.length > 0,
    hasFigures: chartOutputs.length > 0,
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
  uiStore.setActiveTab('output')
  appStore.setTerminalOutput('Running code...')
  const runMeta = startRunEntry('Code run', appStore.pythonFileContent)
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
    uiStore.setDataPane('output')
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
  const runMeta = startRunEntry('Selection run', selectedCode)

  try {
    await executeSnippet(
      selectedCode,
      'Selected code executed successfully!',
      {
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
    uiStore.setDataPane('output')
  } finally {
    isRunning.value = false
    appStore.setCodeRunning(false)
  }
}

function acceptCompletionOrIndent(view) {
  if (acceptCompletion(view)) return true
  return indentMore(view)
}

function handleEnterWithoutAutocompleteAccept(view) {
  if (completionStatus(view.state)) {
    return insertNewlineAndIndent(view)
  }
  return false
}

const customKeymap = [
  ...searchKeymap,
  { key: 'Tab', run: acceptCompletionOrIndent },
  { key: 'Enter', run: handleEnterWithoutAutocompleteAccept },
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

function syncEditorEditability() {
  if (!editor) return
  editor.dispatch({
    effects: editableCompartment.reconfigure(EditorView.editable.of(!isGeneratingCode.value))
  })
}

function readEditorMonoFont() {
  if (typeof window === 'undefined' || !window.getComputedStyle) {
    return '"JetBrainsMono Nerd Font", "JetBrains Mono", monospace'
  }
  const resolved = window.getComputedStyle(document.documentElement).getPropertyValue('--font-mono').trim()
  return resolved || '"JetBrainsMono Nerd Font", "JetBrains Mono", monospace'
}

function buildEditorThemeExtension() {
  const editorMonoFont = readEditorMonoFont()
  return EditorView.theme({
    '&': { fontSize: '14px', height: '100%', backgroundColor: 'var(--color-base)' },
    '.cm-editor': { backgroundColor: 'var(--color-base)' },
    '.cm-scroller': { fontFamily: editorMonoFont, backgroundColor: 'var(--color-base)' },
    '.cm-gutters': {
      backgroundColor: 'var(--color-surface)',
      borderRight: '1px solid var(--color-border)',
      color: 'var(--color-text-muted)',
    },
    '.cm-content': { padding: '16px' },
    '.cm-focused': { outline: 'none' },
  })
}

function syncEditorTheme() {
  if (!editor) return
  editor.dispatch({
    effects: visualThemeCompartment.reconfigure(buildEditorThemeExtension())
  })
}

async function initializeEditor() {
  if (!editorContainer.value) return

  const extensions = [
    basicSetup,
    editableCompartment.of(EditorView.editable.of(!isGeneratingCode.value)),
    visualThemeCompartment.of(buildEditorThemeExtension()),
    indentUnit.of('    '),
    python(),
    autocompletion({ override: [completionSource] }),
    Prec.highest(keymap.of(customKeymap)),
    EditorView.updateListener.of((update) => {
      // Handle content changes
      if (update.docChanged && !isUpdatingFromStore) {
        const content = update.state.doc.toString()
        const previousContent = update.startState.doc.toString()
        isUpdatingFromStore = true
        appStore.noteUserEditedCode(content, { baselineCode: previousContent })
        setTimeout(() => {
          isUpdatingFromStore = false
        }, 10)
      }

      // Handle cursor position updates
      if (update.selectionSet || update.docChanged) {
        const head = update.state.selection.main.head
        const line = update.state.doc.lineAt(head)
        uiStore.setEditorPosition(line.number, head - line.from + 1)
      }
    }),
    EditorView.domEventHandlers({
      focus: () => {
        uiStore.setEditorFocused(true)
        // Ensure accurate position on initial focus
        if (editor) {
          const head = editor.state.selection.main.head
          const line = editor.state.doc.lineAt(head)
          uiStore.setEditorPosition(line.number, head - line.from + 1)
        }
      },
      blur: () => {
        uiStore.setEditorFocused(false)
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

async function downloadCode() {
  try {
    const code = appStore.pythonFileContent || '# No code in editor'
    const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-')
    const filename = `python_code_${timestamp}.py`
    const bytes = new TextEncoder().encode(code)
    const exported = await persistExportFile({
      defaultFileName: filename,
      mimeType: 'text/x-python;charset=utf-8;',
      payload: bytes,
      nativeFilters: [{ name: 'Python file', extensions: ['py'] }],
      browserFileTypes: [{ description: 'Python file', accept: { 'text/x-python': ['.py'] } }],
    })
    if (!exported) {
      toast.info('Export canceled')
      return
    }
    toast.success('Export complete', `${filename} saved.`)
  } catch (error) {
    console.error('Failed to download code:', error)
    toast.error('Export failed', 'Unable to save code file.')
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

  await initializeEditor()
})

onUnmounted(() => {
  if (editor) editor.destroy()
})

watch(() => appStore.generatedCode, (newCode) => {
  if (newCode && appStore.codeEditorSource === 'agent' && !appStore.hasUserEditedCode) {
    appStore.setPythonFileContent(newCode)
    updateEditorContent()
    isGeneratingCode.value = false
    uiStore.setLoading(false)
    appStore.setCodeRunning(false)
  }
})

watch(() => uiStore.isLoading, (loading) => {
  isGeneratingCode.value = loading
  syncEditorEditability()
})

watch(() => appStore.pythonFileContent, () => {
  if (!isUpdatingFromStore && editor) {
    updateEditorContent()
  }
})

watch(() => appStore.uiCodeFont, () => {
  syncEditorTheme()
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
