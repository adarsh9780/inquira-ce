<template>
  <div class="flex flex-col h-full">
    <!-- Menu Bar -->
    <div class="flex-shrink-0 bg-gray-50 border-b border-gray-200 px-4 py-3">
      <div class="flex items-center justify-between">
      <div class="flex items-center space-x-2">
        <!-- Run Button (available in both modes) -->
        <button
          @click="runCode"
          :disabled="!canRunCode || isRunning"
            :title="appStore.isNotebookMode ? 'Run All Cells (R)' : 'Run Code (R)'"
            class="inline-flex items-center px-2 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white transition-colors"
            :class="canRunCode && !isRunning
              ? 'bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500'
              : 'bg-gray-400 cursor-not-allowed'"
          >
            <PlayIcon v-if="!isRunning" class="h-4 w-4" />
          <div v-else class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
        </button>

        <!-- Sync Table Name Button -->
        <button
          @click="syncTableNameInCode"
          :title="'Sync table name in code to current data file'"
          class="inline-flex items-center px-2 py-2 border border-gray-300 text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
        >
          <ArrowPathIcon class="h-4 w-4" />
        </button>

          <!-- Undo Button -->
          <button
            @click="undo"
            :disabled="!canUndo || appStore.isNotebookMode"
            class="inline-flex items-center px-2 py-2 border border-gray-300 text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
            :class="(!canUndo || appStore.isNotebookMode) ? 'opacity-50 cursor-not-allowed' : ''"
            :title="appStore.isNotebookMode ? 'Undo not available in Cell mode' : 'Undo (Ctrl+Z)'"
          >
            <ArrowUturnLeftIcon class="h-4 w-4" />
          </button>

          <!-- Redo Button -->
          <button
            @click="redo"
            :disabled="!canRedo || appStore.isNotebookMode"
            class="inline-flex items-center px-2 py-2 border border-gray-300 text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
            :class="(!canRedo || appStore.isNotebookMode) ? 'opacity-50 cursor-not-allowed' : ''"
            :title="appStore.isNotebookMode ? 'Redo not available in Cell mode' : 'Redo (Ctrl+Y)'"
          >
            <ArrowUturnRightIcon class="h-4 w-4" />
          </button>

          <!-- Download Button (available in both modes) -->
          <button
            @click="downloadCode"
            :disabled="!appStore.pythonFileContent && !appStore.isNotebookMode"
            class="inline-flex items-center px-2 py-2 border border-gray-300 text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
            :class="(!appStore.pythonFileContent && !appStore.isNotebookMode) ? 'opacity-50 cursor-not-allowed' : ''"
          >
            <ArrowDownTrayIcon class="h-4 w-4" />
          </button>

          <!-- Notebook Mode Toggle -->
          <div class="flex items-center space-x-2">
            <span class="text-sm font-medium text-gray-700">Script</span>
            <input
              type="checkbox"
              class="w-10 h-5 bg-gray-300 rounded-full appearance-none cursor-pointer checked:bg-blue-500 transition-colors relative before:content-[''] before:absolute before:top-0.5 before:left-0.5 before:w-4 before:h-4 before:bg-white before:rounded-full before:transition-transform checked:before:translate-x-5"
              :checked="appStore.isNotebookMode"
              @change="toggleNotebookMode"
              title="Toggle between Script and Cell mode"
            />
            <span class="text-sm font-medium text-gray-700">Cell</span>
          </div>

          <!-- Cell Action Icons (only active in notebook mode) -->
          <div v-if="appStore.isNotebookMode" class="flex items-center space-x-1 ml-4 pl-4 border-l border-gray-300">
            <!-- Run Active Cell -->
            <button
              @click="runActiveCell"
              :disabled="!canRunActiveCell"
              class="px-2 py-2 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              title="Run active cell"
            >
              <PlayIcon class="h-4 w-4" />
            </button>

            <!-- Add Cell Above -->
            <button
              @click="addCellAboveActive"
              class="px-2 py-2 text-gray-400 hover:text-gray-600 hover:bg-gray-200 rounded transition-colors"
              title="Add cell above active cell"
            >
              <ChevronUpIcon class="h-4 w-4" />
            </button>

            <!-- Add Cell Below -->
            <button
              @click="addCellBelowActive"
              class="px-2 py-2 text-gray-400 hover:text-gray-600 hover:bg-gray-200 rounded transition-colors"
              title="Add cell below active cell"
            >
              <ChevronDownIcon class="h-4 w-4" />
            </button>

            <!-- Delete Cell -->
            <button
              @click="deleteActiveCell"
              :disabled="appStore.notebookCells.length <= 1"
              class="px-2 py-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              title="Delete active cell"
            >
              <XMarkIcon class="h-4 w-4" />
            </button>

            <!-- Split Cell -->
            <button
              @click="splitActiveCell"
              class="px-2 py-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
              title="Split active cell (Ctrl+Shift+-)"
            >
              <ScissorsIcon class="h-4 w-4" />
            </button>

            <!-- Join Cells -->
            <button
              @click="joinSelectedCells"
              class="px-2 py-2 text-gray-400 hover:text-purple-600 hover:bg-purple-50 rounded transition-colors"
              title="Join selected cells (Ctrl+Shift++)"
            >
              <RectangleStackIcon class="h-4 w-4" />
            </button>
          </div>

          <!-- Cell Action Icons (disabled in script mode) -->
          <div v-else class="flex items-center space-x-1 ml-4 pl-4 border-l border-gray-300">
            <!-- Run Active Cell (disabled) -->
            <button
              disabled
              class="px-2 py-2 text-gray-300 cursor-not-allowed rounded"
              title="Run active cell (only available in Cell mode)"
            >
              <PlayIcon class="h-4 w-4" />
            </button>

            <!-- Add Cell Above (disabled) -->
            <button
              disabled
              class="px-2 py-2 text-gray-300 cursor-not-allowed rounded"
              title="Add cell above (only available in Cell mode)"
            >
              <ChevronUpIcon class="h-4 w-4" />
            </button>

            <!-- Add Cell Below (disabled) -->
            <button
              disabled
              class="px-2 py-2 text-gray-300 cursor-not-allowed rounded"
              title="Add cell below (only available in Cell mode)"
            >
              <ChevronDownIcon class="h-4 w-4" />
            </button>

            <!-- Delete Cell (disabled) -->
            <button
              disabled
              class="px-2 py-2 text-gray-300 cursor-not-allowed rounded"
              title="Delete cell (only available in Cell mode)"
            >
              <XMarkIcon class="h-4 w-4" />
            </button>

            <!-- Split Cell (disabled) -->
            <button
              disabled
              class="px-2 py-2 text-gray-300 cursor-not-allowed rounded"
              title="Split cell (only available in Cell mode)"
            >
              <ScissorsIcon class="h-4 w-4" />
            </button>

            <!-- Join Cells (disabled) -->
            <button
              disabled
              class="px-2 py-2 text-gray-300 cursor-not-allowed rounded"
              title="Join cells (only available in Cell mode)"
            >
              <RectangleStackIcon class="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Conditional Rendering: Notebook Mode or Single Editor -->
    <div v-if="appStore.isNotebookMode" class="flex-1 overflow-y-auto bg-gray-50 p-4">
      <!-- Notebook Cells -->
      <div v-if="appStore.notebookCells.length > 0" class="space-y-4">
        <NotebookCell
          v-for="(cell, index) in appStore.notebookCells"
          :key="cell.id"
          :cell="cell"
          :index="index"
          :total-cells="appStore.notebookCells.length"
          :is-active="index === appStore.activeCellIndex"
          :is-selected="appStore.selectedCellIds.includes(cell.id)"
          @add-cell-above="addCellAbove"
          @add-cell-below="addCellBelow"
          @delete-cell="deleteCell"
          @split-cell="splitCell"
          @join-cells="joinCells"
          @toggle-selection="toggleCellSelection"
          @click="setActiveCell(index)"
        />
      </div>

      <!-- Empty Notebook State -->
      <div
        v-else
        class="flex items-center justify-center h-full"
      >
        <div class="text-center">
          <CodeBracketIcon class="h-12 w-12 text-gray-300 mx-auto mb-3" />
          <p class="text-sm text-gray-500">Start building your notebook</p>
          <p class="text-xs text-gray-400 mt-1">Add cells to organize your Python code</p>
        </div>
      </div>
    </div>

    <!-- Single Editor Mode -->
    <div v-else class="flex-1 relative" style="min-height: 400px;">
      <div
        ref="editorContainer"
        class="w-full h-full"
        style="min-height: 400px; position: relative; z-index: 1; background-color: white;"
      ></div>

      <!-- Loading Overlay for Code Generation -->
      <div
        v-if="isGeneratingCode"
        class="absolute inset-0 flex items-center justify-center bg-white bg-opacity-90 z-10"
      >
        <div class="text-center">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p class="text-sm font-medium text-gray-900">Generating code...</p>
          <p class="text-xs text-gray-500 mt-1">AI is creating Python code for your analysis</p>
        </div>
      </div>

      <!-- Empty State -->
      <div
        v-if="!appStore.pythonFileContent.trim() && !isGeneratingCode"
        class="absolute inset-0 flex items-center justify-center bg-gray-50"
      >
        <div class="text-center">
          <CodeBracketIcon class="h-12 w-12 text-gray-300 mx-auto mb-3" />
          <p class="text-sm text-gray-500">Start writing your Python code</p>
          <p class="text-xs text-gray-400 mt-1">One file per session - your code is automatically saved</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed, nextTick } from 'vue'
import { useAppStore } from '../../stores/appStore'
import { useAuthStore } from '../../stores/authStore'
import apiService from '../../services/apiService'
import executionService from '../../services/executionService'
import { toast } from '../../composables/useToast'
import { normalizeExecutionResponse } from '../../utils/runtimeExecution'
import { buildExecutionViewModel } from '../../utils/executionViewModel'
import NotebookCell from './NotebookCell.vue'

// CodeMirror 6 imports
import { EditorView, basicSetup } from 'codemirror'
import { EditorState } from '@codemirror/state'
import { python } from '@codemirror/lang-python'
import { autocompletion } from '@codemirror/autocomplete'
import { keymap } from '@codemirror/view'
import { searchKeymap } from '@codemirror/search'
import { toggleComment, indentMore, indentLess } from '@codemirror/commands'
import { indentUnit } from '@codemirror/language'

import {
  PlayIcon,
  ArrowDownTrayIcon,
  CodeBracketIcon,
  PlusIcon,
  DocumentTextIcon,
  XMarkIcon,
  ArrowUturnLeftIcon,
  ArrowUturnRightIcon,
  DocumentTextIcon as NotebookIcon,
  ScissorsIcon,
  RectangleStackIcon,
  ChevronUpIcon,
  ChevronDownIcon,
  ArrowPathIcon
} from '@heroicons/vue/24/outline'

const appStore = useAppStore()
const authStore = useAuthStore()

const editorContainer = ref(null)
const isRunning = ref(false)
const isGeneratingCode = ref(false)
const databasePaths = ref(null)
const settingsInfo = ref(null)
let editor = null
let isUpdatingFromStore = false // Flag to prevent feedback loops

// Helper function to get table name from file path (just filename without extension)
function getTableName(filePath) {
  if (!filePath) return 'data'

  // Get filename without extension
  const filename = filePath.split('/').pop().split('.')[0]

  // Return just the filename (no transformations for SQL safety)
  return filename || 'data'
}

// Helper function to get database path
function getDatabasePath() {
  return databasePaths.value?.database_path || null
}

// Fetch database paths from API
async function fetchDatabasePaths() {
  try {
    console.debug('🔄 Fetching database paths from API (/settings/paths)...')
    const paths = await apiService.getDatabasePaths()
    databasePaths.value = paths
    console.debug('✅ Database paths fetched successfully:', paths)
    console.debug('📁 Database path that will be used in code editor:', paths?.database_path)
    console.debug('📁 Schema path:', paths?.schema_path)
    console.debug('📁 Base directory:', paths?.base_directory)
  } catch (error) {
    console.error('❌ Failed to fetch database paths from /settings/paths:', error)
    console.error('❌ Error details:', error.response?.data || error.message)
    console.error('❌ Error status:', error.response?.status)
    // Don't use fallback paths - let the code template handle the case where dbPath is null
    databasePaths.value = null
    console.debug('⚠️ No database paths available, will use fallback file-based approach')
  }
}

// Fetch settings to obtain backend-declared table name (from /settings/view)
async function fetchSettings() {
  try {
    const s = await apiService.getSettings()
    settingsInfo.value = s || null
  } catch (error) {
    console.warn('⚠️ Failed to fetch settings for table name:', error?.message || error)
    settingsInfo.value = null
  }
}

const canRunCode = computed(() => {
  if (appStore.isNotebookMode) {
    // In notebook mode, can run if there are cells with content
    return appStore.notebookCells.some(cell => cell.content.trim()) && !isRunning.value
  } else {
    // In script mode, can run if there's content
    return appStore.pythonFileContent.trim() && !isRunning.value
  }
})

const canUndo = computed(() => {
  return editor && editor.state && editor.state.undoDepth > 0
})

const canRedo = computed(() => {
  return editor && editor.state && editor.state.redoDepth > 0
})

const canRunActiveCell = computed(() => {
  if (!appStore.isNotebookMode) return false
  const activeCellIndex = appStore.activeCellIndex
  if (activeCellIndex < 0 || activeCellIndex >= appStore.notebookCells.length) return false
  const activeCell = appStore.notebookCells[activeCellIndex]
  return activeCell && activeCell.content.trim() && !activeCell.isRunning
})

// Define keymap with access to component functions
const customKeymap = [
  ...searchKeymap,
  // Indentation with Tab / Shift-Tab
  {
    key: 'Tab',
    run: indentMore
  },
  {
    key: 'Shift-Tab',
    run: indentLess
  },
  {
    key: 'Mod-/',
    run: toggleComment
  },
  {
    key: 'Mod-Enter',
    run: () => {
      if (appStore.isNotebookMode) {
        // In notebook mode, Shift+Enter runs current cell
        // This will be handled by individual cells
        return false
      } else if (canRunCode.value) {
        runCode()
        return true
      }
      return false
    }
  },
  {
    key: 'Mod-r',
    run: () => {
      if (canRunCode.value) {
        runCode()
        return true
      }
      return false
    }
  },
  // Notebook mode shortcuts
  {
    key: 'Mod-n',
    run: () => {
      if (appStore.isNotebookMode) {
        toggleNotebookMode()
        return true
      }
      return false
    }
  },
  // Cell split shortcut (Ctrl+Shift+-)
  {
    key: 'Mod-Shift--',
    run: () => {
      if (appStore.isNotebookMode) {
        // Split the active cell - this will be handled by the cell component
        // The actual splitting logic is in the NotebookCell component
        return false // Let the cell component handle this
      }
      return false
    }
  },
  // Cell join shortcut (Ctrl+Shift++)
  {
    key: 'Mod-Shift-=',
    run: () => {
      if (appStore.isNotebookMode) {
        if (appStore.selectedCellIds.length > 1) {
          // Join selected cells
          joinCells(null)
        } else {
          // Join active cell with previous - this will be handled by the cell component
          return false // Let the cell component handle this
        }
        return true
      }
      return false
    }
  }
]

// Computed property for default code template
const defaultCodeTemplate = computed(() => {
  const originalFilepath = appStore.dataFilePath || '/path/to/your/data/file.csv'
  const dbPath = databasePaths.value?.database_path
  const backendTable = settingsInfo?.value?.table_name || settingsInfo?.value?.data_table_name || settingsInfo?.value?.table || null
  const tableName = backendTable || getTableName(originalFilepath)

  // Default template (DuckDB to Narwhals API)
  return `# cell: Load and explore data
import duckdb
import narwhals as nw
import plotly.express as px

# Establish connection and set table name
table_name = "${tableName}"
try:
    conn  # type: ignore  # noqa
except NameError:
    conn = duckdb.connect(r"${dbPath || ''}") if "${dbPath || ''}".strip() else duckdb.connect()

# cell: Quick sample
# Use DuckDB for lazy evaluation, then convert to a Narwhals-compatible DataFrame
lazy_query = conn.sql(f"SELECT * FROM {table_name} LIMIT 10")
df = nw.from_native(lazy_query.pl(), eager=True)
df

# cell: Schema + summary
# Use DuckDB for efficient aggregations and metadata extraction
schema_df = nw.from_native(conn.sql(f"DESCRIBE SELECT * FROM {table_name}").pl(), eager=True)
row_count_df = nw.from_native(conn.sql(f"SELECT COUNT(*) AS rows FROM {table_name}").pl(), eager=True)

schema_df, row_count_df
`
})

// Replace table_name assignment in given Python source
function replaceTableNameInCode(src, newName) {
  if (!src || !newName) return src
  // Matches: table_name = "..." or '...'
  const re = /(\n|^)\s*table_name\s*=\s*(["'])(.*?)\2/g
  // Replace all occurrences conservatively
  return src.replace(re, (m, p1, quote) => `${p1}table_name = ${quote}${newName}${quote}`)
}

async function syncTableNameInCode(silent = false) {
  // Refresh settings to get updated backend table name
  await fetchSettings()
  const originalFilepath = appStore.dataFilePath || ''
  const backendTable = settingsInfo?.value?.table_name || settingsInfo?.value?.data_table_name || settingsInfo?.value?.table || null
  const tableName = backendTable || getTableName(originalFilepath)

  if (appStore.isNotebookMode) {
    // Update in all notebook cells
    const cells = appStore.notebookCells
    let changed = false
    cells.forEach((cell) => {
      const updated = replaceTableNameInCode(cell.content, tableName)
      if (updated !== cell.content) {
        appStore.updateNotebookCell(cell.id, { content: updated })
        changed = true
      }
    })
    if (!silent) {
      if (changed) {
        toast.success('Synced table name in notebook cells')
      } else {
        toast.info('No table_name assignment found in cells')
      }
    }
    return
  }

  // Script mode
  const current = appStore.pythonFileContent
  const updated = replaceTableNameInCode(current, tableName)
  if (updated !== current) {
    appStore.setPythonFileContent(updated)
    updateEditorContent()
    if (!silent) toast.success('Synced table name in code')
  } else if (isDefaultEditorContent(current.trim())) {
    // If default template, refresh entirely to pick up table name too
    appStore.setPythonFileContent(defaultCodeTemplate.value)
    updateEditorContent()
    if (!silent) toast.success('Refreshed code template with new table name')
  } else {
    if (!silent) toast.info('No table_name assignment found to update')
  }
}

onMounted(async () => {
  await nextTick()

  // Fetch database paths from API
  await fetchSettings()
  await fetchDatabasePaths()

  // Attempt a silent sync of table name on mount in case data path changed
  await syncTableNameInCode(true)

  // Load default code if no code exists or only has minimal content
  const currentContent = appStore.pythonFileContent.trim()
  if (!currentContent || currentContent === '# Python code for data analysis') {
    console.debug('Loading default code template')
    appStore.setPythonFileContent(defaultCodeTemplate.value)
  }

  await initializeEditor()
})

onUnmounted(() => {
  if (editor) {
    editor.destroy()
  }
})

// Watch for generated code changes
watch(() => appStore.generatedCode, (newCode) => {
  if (newCode) {
    if (appStore.isNotebookMode) {
      // In notebook mode, update the active cell with generated code
      const activeCellIndex = appStore.activeCellIndex
      if (activeCellIndex >= 0 && activeCellIndex < appStore.notebookCells.length) {
        const activeCell = appStore.notebookCells[activeCellIndex]
        appStore.updateNotebookCell(activeCell.id, { content: newCode })
      }
    } else {
      // In script mode, update the session file with generated code
      appStore.setPythonFileContent(newCode)
      updateEditorContent()
    }
    // Clear the generating state
    isGeneratingCode.value = false
    appStore.setLoading(false) // Clear loading state for code generation
    appStore.setCodeRunning(false) // Clear global code running state
  }
})

// Watch for loading state changes to show generating indicator
watch(() => appStore.isLoading, (isLoading) => {
  isGeneratingCode.value = isLoading
  // Don't set code running here to avoid conflicts with execution state
})

// Watch for python file content changes from external sources (not from editor itself)
watch(() => appStore.pythonFileContent, (newContent) => {
  if (!isUpdatingFromStore && editor) {
    updateEditorContent()
  }
})

// Watch for notebook mode changes to ensure editor is properly initialized
watch(() => appStore.isNotebookMode, async (newMode, oldMode) => {
  console.debug('🔄 MODE SWITCH:', { newMode, oldMode, currentMode: appStore.isNotebookMode })

  if (newMode === false && oldMode === true) {
    console.debug('🔄 Switching to script mode - checking editor state...')
    console.debug('🔍 Editor exists:', !!editor)
    console.debug('🔍 Editor container exists:', !!editorContainer.value)

    // Switching from notebook mode to script mode
    // Ensure editor is initialized and updated with the combined content
    await nextTick()

    // Wait a bit more for DOM to be fully ready
    setTimeout(async () => {
      console.debug('⏰ After delay - Editor:', !!editor, 'Container:', !!editorContainer.value)

      if (!editor && editorContainer.value) {
        console.debug('📝 Initializing new editor...')
        await initializeEditor()
      } else if (editor) {
        console.debug('🔄 Updating existing editor content...')

        // CRITICAL FIX: Re-attach the editor DOM to the container
        setTimeout(() => {
          const container = editorContainer.value
          console.debug('🔍 Editor DOM before reattach:', editor.dom)
          console.debug('🔍 Container before reattach:', container)
          console.debug('🔍 Container children before:', container?.children)

          if (container && editor.dom) {
            // Check if editor DOM is already in the container
            if (!container.contains(editor.dom)) {
              console.debug('🔄 Re-attaching editor DOM to container...')
              // Clear container first
              container.innerHTML = ''
              // Re-attach the editor DOM
              container.appendChild(editor.dom)
              console.debug('✅ Editor DOM re-attached to container')
            } else {
              console.debug('ℹ️ Editor DOM already in container')
            }

            // Force visibility
            editor.dom.style.display = 'block'
            editor.dom.style.visibility = 'visible'
            editor.dom.style.opacity = '1'

            console.debug('🔍 Container children after reattach:', container.children)
            console.debug('🔍 Editor DOM after reattach:', editor.dom)
          }

          updateEditorContent()
        }, 50)
      } else {
        console.debug('⚠️ Editor container not ready')
        // Retry after another delay
        setTimeout(async () => {
          if (!editor && editorContainer.value) {
            console.debug('📝 Retrying editor initialization...')
            await initializeEditor()
          }
        }, 100)
      }
    }, 50)
  }
})

// This watcher is now handled by the consolidated dataFilePath watcher above

// Watch for default code template changes and update editor
// Helper: detect if editor content is effectively the default template
function isDefaultEditorContent(content) {
  const current = (content || '').trim()
  return (
    current === '' ||
    current === '# Python code for data analysis' ||
    (current.startsWith('# Python code for data analysis') && !current.includes('import pandas'))
  )
}

watch(() => defaultCodeTemplate.value, (newTemplate) => {
  // Only update if the current content is still the default template
  const currentContent = appStore.pythonFileContent.trim()
  if (isDefaultEditorContent(currentContent) && newTemplate !== currentContent) {
    console.debug('Updating editor with new default code template')
    appStore.setPythonFileContent(newTemplate)
  }
})

// Watch for data file path changes and only update code if it's still the default template
watch(() => appStore.dataFilePath, (newPath, oldPath) => {
  if (newPath !== oldPath) {
    // Only update if the current content is still the default template
    const currentContent = appStore.pythonFileContent.trim()
    if (isDefaultEditorContent(currentContent)) {
      console.debug('Updating code template due to data file path change')
      appStore.setPythonFileContent(defaultCodeTemplate.value)
    }
  }
})

// Watch for database paths changes and update code template
watch(() => databasePaths.value, (newPaths) => {
  if (newPaths?.database_path) {
    // Only update if the current content is still the default template
    const currentContent = appStore.pythonFileContent.trim()
    if (isDefaultEditorContent(currentContent)) {
      console.debug('Updating code template due to database paths change')
      appStore.setPythonFileContent(defaultCodeTemplate.value)
    }
  }
})

// Watch for user changes and refetch database paths
watch(() => authStore.userId, async (newUserId, oldUserId) => {
  if (newUserId !== oldUserId && newUserId) {
    console.debug('User changed, refetching database paths')
    await fetchDatabasePaths()
  }
})

async function initializeEditor() {
  if (!editorContainer.value) {
    console.debug('❌ Editor container not found')
    return
  }

  console.debug('📝 Initializing CodeMirror editor...', editorContainer.value)

  try {
    const extensions = [
      basicSetup,
      indentUnit.of('    '),
      python(),
      autocompletion(),
      keymap.of(customKeymap),
      EditorView.theme({
        '&': {
          fontSize: '14px',
          height: '100%',
          display: 'block',
          visibility: 'visible'
        },
        '.cm-content': {
          padding: '16px',
          minHeight: '100%',
          display: 'block',
          visibility: 'visible'
        },
        '.cm-focused': {
          outline: 'none'
        },
        '.cm-editor': {
          height: '100%',
          display: 'block',
          visibility: 'visible'
        },
        '.cm-scroller': {
          fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace',
          display: 'block',
          visibility: 'visible'
        }
      }),
      EditorView.updateListener.of((update) => {
        if (update.docChanged && !isUpdatingFromStore) {
          const content = editor.state.doc.toString()
          // Prevent triggering the watcher while updating from editor
          isUpdatingFromStore = true
          appStore.setPythonFileContent(content)
          // Reset flag after a short delay
          setTimeout(() => {
            isUpdatingFromStore = false
          }, 10)
        }
      })
    ]

    const state = EditorState.create({
      doc: appStore.pythonFileContent,
      extensions
    })

    editor = new EditorView({
      state,
      parent: editorContainer.value
    })

    console.debug('✅ CodeMirror editor initialized successfully', editor)

  } catch (error) {
    console.error('❌ Failed to initialize CodeMirror Editor:', error)
  }
}

function updateEditorContent() {
  if (editor && !isUpdatingFromStore) {
    const content = appStore.pythonFileContent
    const currentContent = editor.state.doc.toString()

    // Only update if content is actually different
    if (currentContent !== content) {
      isUpdatingFromStore = true
      const transaction = editor.state.update({
        changes: {
          from: 0,
          to: editor.state.doc.length,
          insert: content
        }
      })
      editor.dispatch(transaction)

      // Reset flag after update
      setTimeout(() => {
        isUpdatingFromStore = false
      }, 10)
    }
  }
}

function applyExecutionArtifactsToStore(viewModel, { switchTabs = false } = {}) {
  appStore.setDataframes(viewModel.dataframes)
  if (viewModel.dataframes.length > 0) {
    appStore.setResultData(viewModel.dataframes[0].data)
    if (switchTabs) appStore.setActiveTab('table')
  }

  appStore.setFigures(viewModel.figures)
  if (viewModel.figures.length > 0) {
    appStore.setPlotlyFigure(viewModel.figures[0].data)
    if (switchTabs) appStore.setActiveTab('figure')
  }

  appStore.setScalars(viewModel.scalars)
  if (viewModel.scalars.length > 0 && switchTabs) {
    appStore.setActiveTab('terminal')
  }
}

function buildCellExecutionViewModel(response, executionTime, mode = 'available') {
  const locationWord = mode === 'displayed' ? 'Displayed' : 'Available'
  return buildExecutionViewModel(
    {
      ...response,
      execution_time: executionTime,
    },
    {
      dataframeLine: (count) => `✅ ${count} dataframe(s) found. ${locationWord} in Table tab.`,
      figureLine: (count) => `✅ ${count} figure(s) found. ${locationWord} in Chart tab.`,
      scalarLine: (count) => `✅ ${count} scalar(s) found. ${locationWord} in Terminal tab.`,
      successLine: '✅ Cell executed successfully!',
    },
  )
}

async function runCode() {
  if (!canRunCode.value) return

  isRunning.value = true
  appStore.setCodeRunning(true)

  if (appStore.isNotebookMode) {
    // Run all notebook cells
    appStore.setTerminalOutput('Running all cells...')

    try {
      // Execute each cell sequentially
      for (let i = 0; i < appStore.notebookCells.length; i++) {
        const cell = appStore.notebookCells[i]
        if (!cell.content.trim()) continue

        appStore.updateNotebookCell(cell.id, { isRunning: true, output: '' })

        try {
          const start = performance.now()
          const pyResponse = await executionService.executePython(cell.content)
          const execTime = (performance.now() - start) / 1000
          const normalized = normalizeExecutionResponse({
            success: pyResponse.success,
            stdout: pyResponse.stdout,
            stderr: pyResponse.stderr,
            error: pyResponse.error,
            result: pyResponse.result,
            result_type: pyResponse.resultType,
          })
          const viewModel = buildCellExecutionViewModel(normalized, execTime, 'displayed')
          applyExecutionArtifactsToStore(viewModel, { switchTabs: true })
          appStore.updateNotebookCell(cell.id, { output: viewModel.output, isRunning: false })

        } catch (cellError) {
          console.error(`Cell ${i + 1} execution failed:`, cellError)
          const errorMessage = cellError.response?.data?.detail || cellError.message || 'Cell execution failed'
          appStore.updateNotebookCell(cell.id, {
            output: `❌ Error: ${errorMessage}`,
            isRunning: false
          })

          if (cellError.response?.status === 400) {
            toast.error(`Cell ${i + 1} Execution Failed`, 'Please check your code syntax and try again.')
          } else if (cellError.response?.status === 408 || cellError.code === 'TIMEOUT') {
            toast.error(`Cell ${i + 1} Execution Timeout`, 'Cell execution took too long. Please try with simpler code.')
          } else {
            toast.error(`Cell ${i + 1} Execution Failed`, 'An error occurred while running the cell.')
          }
        }
      }

      appStore.setTerminalOutput('All cells executed successfully!')

    } catch (error) {
      console.error('Notebook execution failed:', error)
      appStore.setTerminalOutput(`Error executing notebook: ${error.message}`)
    } finally {
      // Ensure global running state clears for notebook mode as well
      isRunning.value = false
      appStore.setCodeRunning(false)
    }

  } else {
    // Run single script
    appStore.setTerminalOutput('Running code...')

    try {
      const code = appStore.pythonFileContent

      // Execute code using the API service
      const start = performance.now()
      const pyResponse = await executionService.executePython(code)
      const execTime = (performance.now() - start) / 1000
      const normalized = normalizeExecutionResponse({
        success: pyResponse.success,
        stdout: pyResponse.stdout,
        stderr: pyResponse.stderr,
        error: pyResponse.error,
        result: pyResponse.result,
        result_type: pyResponse.resultType,
      })
      const viewModel = buildExecutionViewModel(
        {
          ...normalized,
          execution_time: execTime,
        },
        {
          successLine: 'Code executed successfully!',
          includeVariableSummary: true,
        },
      )
      applyExecutionArtifactsToStore(viewModel)
      appStore.setTerminalOutput(viewModel.output)

      // Results are available in respective tabs but don't auto-switch
      // Users can manually navigate to view results

    } catch (error) {
      console.error('Code execution failed:', error)
      const errorMessage = error.response?.data?.detail || error.message || 'Code execution failed'

      // Show toast notification for execution errors
      if (error.response?.status === 400) {
        toast.error('Code Execution Failed', 'Please check your code syntax and try again.')
      } else if (error.response?.status === 408 || error.code === 'TIMEOUT') {
        toast.error('Execution Timeout', 'Code execution took too long. Please try with simpler code.')
      } else if (error.response?.status >= 500) {
        toast.error('Server Error', 'The server encountered an error during code execution.')
      } else if (error.code === 'NETWORK_ERROR' || !navigator.onLine) {
        toast.error('Network Error', 'Unable to execute code. Please check your connection.')
      } else {
        toast.error('Execution Failed', 'An error occurred while running your code.')
      }

      appStore.setTerminalOutput(`Error: ${errorMessage}`)

      // For errors, stay in current tab - users can manually navigate if needed
    } finally {
      isRunning.value = false
      appStore.setCodeRunning(false)
    }
  }
}

function downloadCode() {
  try {
    let code = ''

    if (appStore.isNotebookMode) {
      // Combine all notebook cell contents
      code = appStore.notebookCells.map(cell => cell.content).join('\n\n')
    } else {
      // Get the Python code from the single editor
      code = appStore.pythonFileContent || '# No code in editor'
    }

    // Create a blob with the code
    const blob = new Blob([code], { type: 'text/plain' })

    // Create a download link
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url

    // Generate filename with timestamp
    const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-')
    const mode = appStore.isNotebookMode ? 'notebook' : 'code'
    link.download = `python_${mode}_${timestamp}.py`

    // Trigger download
    document.body.appendChild(link)
    link.click()

    // Clean up
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    console.debug('Python code downloaded successfully')
  } catch (error) {
    console.error('Failed to download code:', error)
  }
}

function undo() {
  if (editor && canUndo.value) {
    editor.dispatch(editor.state.undo())
  }
}

function redo() {
  if (editor && canRedo.value) {
    editor.dispatch(editor.state.redo())
  }
}

function toggleNotebookMode(eventOrValue) {
  // Supports being called from DOM events, keymaps, or direct boolean
  let newMode
  if (typeof eventOrValue === 'boolean') {
    newMode = eventOrValue
  } else if (eventOrValue && typeof eventOrValue === 'object' && 'target' in eventOrValue) {
    newMode = !!eventOrValue.target?.checked
  } else {
    newMode = !appStore.isNotebookMode
  }
  appStore.setNotebookMode(newMode)

  if (newMode) {
    // Switching to notebook mode - parse cells from script content
    parseCellsFromScript()
  } else {
    // Switching back to single editor mode - combine all cell contents with cell markers
    const combinedContent = appStore.notebookCells
      .map((cell, index) => {
        const content = cell.content.trim()
        if (!content) return '' // Skip empty cells

        // Check if the cell already has a properly formatted title comment
        const firstLine = content.split('\n')[0].trim()
        const cellCommentMatch = firstLine.match(/^#\s*cell(?:\s+\d+)?\s*:\s*(.+)$/i)

        if (cellCommentMatch) {
          // Cell already has a properly formatted title comment, use content as is
          // For non-first cells, add a separator before the existing content
          const separator = index === 0 ? '' : '\n\n'
          return separator + content
        } else {
          // Cell doesn't have a title comment, add a default one
          const cellMarker = index === 0 ? '' : `\n# cell: Write your Python code here\n`
          return cellMarker + content
        }
      })
      .filter(content => content) // Remove empty entries
      .join('\n\n')

    appStore.setPythonFileContent(combinedContent || '# Python code for data analysis\n# cell: Write your Python code here')
  }
}

function parseCellsFromScript() {
  const scriptContent = appStore.pythonFileContent.trim()

  if (!scriptContent || scriptContent === '# Python code for data analysis') {
    // Create default cell
    appStore.clearNotebookCells()
    appStore.addNotebookCell({
      content: '# cell: Write your Python code here'
    })
    return
  }

  // Split content by "# cell: <title>" comments with backward compatibility.
  const cellPattern = /(?=^\s*#\s*cell(?:\s+\d+)?\s*:)/gim
  const parts = scriptContent.split(cellPattern)

  appStore.clearNotebookCells()

  // Process each part
  for (let i = 0; i < parts.length; i++) {
    const cellContent = parts[i].trim()

    // Skip empty parts
    if (!cellContent) continue

    // Check if this part starts with a cell comment that has a title
    const lines = cellContent.split('\n')
    const firstLine = lines[0].trim()

    // If the first line is a cell comment with title, keep it as is
    const cellCommentMatch = firstLine.match(/^#\s*cell(?:\s+\d+)?\s*:\s*(.+)$/i)
    if (cellCommentMatch) {
      const title = cellCommentMatch[1]?.trim() || 'Write your Python code here'
      const rest = lines.slice(1).join('\n').trim()
      const normalized = `# cell: ${title}${rest ? `\n${rest}` : ''}`
      appStore.addNotebookCell({ content: normalized })
    } else {
      // This doesn't start with a cell comment, treat as regular content
      appStore.addNotebookCell({ content: cellContent })
    }
  }

  // If no cells were created (no "# cell" comments found), create single cell
  if (appStore.notebookCells.length === 0) {
    appStore.addNotebookCell({
      content: scriptContent
    })
  }
}

function addCellAbove(index) {
  appStore.addNotebookCell({
    content: '# cell: Write your Python code here'
  }, index)
}

function addCellBelow(index) {
  appStore.addNotebookCell({
    content: '# cell: Write your Python code here'
  }, index + 1)
}

function deleteCell(cellId) {
  appStore.deleteNotebookCell(cellId)
}

function setActiveCell(index) {
  appStore.setActiveCellIndex(index)
}

function toggleCellSelection(cellId) {
  appStore.toggleCellSelection(cellId)
}

function splitCell(splitData) {
  const { cellId, beforeContent, afterContent } = splitData

  // Find the cell index
  const cellIndex = appStore.notebookCells.findIndex(cell => cell.id === cellId)
  if (cellIndex === -1) return

  // Update the current cell with content before cursor
  appStore.updateNotebookCell(cellId, { content: beforeContent })

  // Add new cell below with content after cursor
  appStore.addNotebookCell({
    content: afterContent
  }, cellIndex + 1)

  // Set focus to the new cell
  setTimeout(() => {
    appStore.setActiveCellIndex(cellIndex + 1)
  }, 100)
}

function joinCells(cellId) {
  // If there are selected cells, join all selected cells
  if (appStore.selectedCellIds.length > 1) {
    const selectedCells = appStore.notebookCells.filter(cell => appStore.selectedCellIds.includes(cell.id))
    if (selectedCells.length < 2) return

    // Sort by index to maintain order
    selectedCells.sort((a, b) => {
      const indexA = appStore.notebookCells.findIndex(cell => cell.id === a.id)
      const indexB = appStore.notebookCells.findIndex(cell => cell.id === b.id)
      return indexA - indexB
    })

    // Combine content of all selected cells
    const combinedContent = selectedCells.map(cell => cell.content).join('\n\n')

    // Update the first cell with combined content
    appStore.updateNotebookCell(selectedCells[0].id, { content: combinedContent })

    // Delete the other selected cells
    for (let i = 1; i < selectedCells.length; i++) {
      appStore.deleteNotebookCell(selectedCells[i].id)
    }

    // Clear selection and set focus to the combined cell
    appStore.clearCellSelection()
    const firstCellIndex = appStore.notebookCells.findIndex(cell => cell.id === selectedCells[0].id)
    appStore.setActiveCellIndex(firstCellIndex)
  } else {
    // Fallback to single cell join (join with previous cell)
    const cellIndex = appStore.notebookCells.findIndex(cell => cell.id === cellId)
    if (cellIndex === -1 || cellIndex === 0) return // Can't join first cell

    const currentCell = appStore.notebookCells[cellIndex]
    const previousCell = appStore.notebookCells[cellIndex - 1]

    // Combine content with a newline separator
    const combinedContent = previousCell.content + '\n\n' + currentCell.content

    // Update the previous cell with combined content
    appStore.updateNotebookCell(previousCell.id, { content: combinedContent })

    // Delete the current cell
    appStore.deleteNotebookCell(cellId)

    // Set focus to the combined cell
    appStore.setActiveCellIndex(cellIndex - 1)
  }
}

function deleteActiveCell() {
  const activeCellIndex = appStore.activeCellIndex
  if (activeCellIndex < 0 || activeCellIndex >= appStore.notebookCells.length) return
  if (appStore.notebookCells.length <= 1) return // Can't delete the last cell

  const activeCell = appStore.notebookCells[activeCellIndex]
  deleteCell(activeCell.id)
}

function splitActiveCell() {
  // Get the active cell
  const activeCellIndex = appStore.activeCellIndex
  if (activeCellIndex < 0 || activeCellIndex >= appStore.notebookCells.length) return

  const activeCell = appStore.notebookCells[activeCellIndex]

  // For menu bar split, we need to split at the middle of the content
  const content = activeCell.content
  const middleIndex = Math.floor(content.length / 2)

  // Find a good split point (preferably at a line break)
  let splitIndex = middleIndex
  const beforeMiddle = content.substring(0, middleIndex)
  const afterMiddle = content.substring(middleIndex)

  // Try to find a line break near the middle
  const lastLineBreakBefore = beforeMiddle.lastIndexOf('\n')
  const firstLineBreakAfter = afterMiddle.indexOf('\n')

  if (lastLineBreakBefore !== -1 && (middleIndex - lastLineBreakBefore) < 50) {
    splitIndex = lastLineBreakBefore + 1 // Include the line break in the first part
  } else if (firstLineBreakAfter !== -1 && firstLineBreakAfter < 50) {
    splitIndex = middleIndex + firstLineBreakAfter + 1
  }

  const beforeContent = content.substring(0, splitIndex).trim()
  const afterContent = content.substring(splitIndex).trim()

  // Update the current cell with content before split
  appStore.updateNotebookCell(activeCell.id, { content: beforeContent })

  // Add new cell below with content after split
  appStore.addNotebookCell({
    content: afterContent
  }, activeCellIndex + 1)

  // Set focus to the new cell
  setTimeout(() => {
    appStore.setActiveCellIndex(activeCellIndex + 1)
  }, 100)
}

function joinSelectedCells() {
  // If there are selected cells, join all selected cells
  if (appStore.selectedCellIds.length > 1) {
    const selectedCells = appStore.notebookCells.filter(cell => appStore.selectedCellIds.includes(cell.id))
    if (selectedCells.length < 2) return

    // Sort by index to maintain order
    selectedCells.sort((a, b) => {
      const indexA = appStore.notebookCells.findIndex(cell => cell.id === a.id)
      const indexB = appStore.notebookCells.findIndex(cell => cell.id === b.id)
      return indexA - indexB
    })

    // Combine content of all selected cells
    const combinedContent = selectedCells.map(cell => cell.content).join('\n\n')

    // Update the first cell with combined content
    appStore.updateNotebookCell(selectedCells[0].id, { content: combinedContent })

    // Delete the other selected cells
    for (let i = 1; i < selectedCells.length; i++) {
      appStore.deleteNotebookCell(selectedCells[i].id)
    }

    // Clear selection and set focus to the combined cell
    appStore.clearCellSelection()
    const firstCellIndex = appStore.notebookCells.findIndex(cell => cell.id === selectedCells[0].id)
    appStore.setActiveCellIndex(firstCellIndex)
  } else {
    // If no cells are selected, join the active cell with the previous one
    const activeCellIndex = appStore.activeCellIndex
    if (activeCellIndex <= 0 || activeCellIndex >= appStore.notebookCells.length) return

    const currentCell = appStore.notebookCells[activeCellIndex]
    const previousCell = appStore.notebookCells[activeCellIndex - 1]

    // Combine content with a newline separator
    const combinedContent = previousCell.content + '\n\n' + currentCell.content

    // Update the previous cell with combined content
    appStore.updateNotebookCell(previousCell.id, { content: combinedContent })

    // Delete the current cell
    appStore.deleteNotebookCell(currentCell.id)

    // Set focus to the combined cell
    appStore.setActiveCellIndex(activeCellIndex - 1)
  }
}

function addCellAboveActive() {
  const activeCellIndex = appStore.activeCellIndex
  if (activeCellIndex < 0 || activeCellIndex >= appStore.notebookCells.length) return

  addCellAbove(activeCellIndex)
}

function addCellBelowActive() {
  const activeCellIndex = appStore.activeCellIndex
  if (activeCellIndex < 0 || activeCellIndex >= appStore.notebookCells.length) return

  addCellBelow(activeCellIndex)
}

async function runActiveCell() {
  const activeCellIndex = appStore.activeCellIndex
  if (activeCellIndex < 0 || activeCellIndex >= appStore.notebookCells.length) return

  const activeCell = appStore.notebookCells[activeCellIndex]
  if (!activeCell.content.trim() || activeCell.isRunning) return

  // Update cell to running state
  appStore.updateNotebookCell(activeCell.id, { isRunning: true, output: '' })

  try {
    const response = await apiService.executeCode(activeCell.content)
    const viewModel = buildCellExecutionViewModel(response, response.execution_time, 'displayed')
    applyExecutionArtifactsToStore(viewModel, { switchTabs: true })
    appStore.updateNotebookCell(activeCell.id, { output: viewModel.output, isRunning: false })

  } catch (error) {
    console.error('Active cell execution failed:', error)
    const errorMessage = error.response?.data?.detail || error.message || 'Cell execution failed'
    appStore.updateNotebookCell(activeCell.id, {
      output: `❌ Error: ${errorMessage}`,
      isRunning: false
    })

    if (error.response?.status === 400) {
      toast.error('Cell Execution Failed', 'Please check your code syntax and try again.')
    } else if (error.response?.status === 408 || error.code === 'TIMEOUT') {
      toast.error('Execution Timeout', 'Cell execution took too long. Please try with simpler code.')
    } else {
      toast.error('Execution Failed', 'An error occurred while running the cell.')
    }
  }
}
</script>

<style scoped>
/* CodeMirror styling is handled by the editor itself */
</style>
