<template>
  <div
    class="notebook-cell border rounded-lg mb-4 bg-white cursor-pointer"
    :class="[
      isSelected ? 'border-blue-500 bg-blue-50' : 'border-gray-200',
      isActive ? 'ring-2 ring-green-500' : ''
    ]"
    @click="handleCellClick"
    @keydown="handleKeydown"
  >
    <!-- Cell Header -->
    <div class="flex items-center justify-between px-4 py-2 bg-gray-50 border-b border-gray-200 rounded-t-lg">
      <div class="flex items-center space-x-2">
        <div class="w-2 h-2 rounded-full" :class="isActive ? 'bg-green-500' : 'bg-blue-500'"></div>
        <!-- Execution Status Indicator -->
        <div class="flex items-center space-x-1">
          <div
            class="w-2 h-2 rounded-full"
            :class="executionStatusClass"
            :title="executionStatusTitle"
          ></div>
        </div>
        <!-- Editable Title -->
        <input
          v-model="titleDraft"
          @blur="saveTitle"
          @keydown.enter.stop.prevent="saveTitle"
          @click.stop
          @mousedown.stop
          class="text-sm font-medium text-gray-700 bg-transparent border border-transparent focus:border-blue-300 focus:ring-0 rounded px-1 py-0.5 w-56"
          :placeholder="`Cell ${index + 1}`"
        />
      </div>

      <div class="flex items-center space-x-1">
        <!-- Run Button -->
        <button
          @click.stop="runCell"
          :disabled="!cell.content.trim() || cell.isRunning"
          class="p-1.5 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded disabled:opacity-50 disabled:cursor-not-allowed"
          title="Run cell"
        >
          <PlayIcon v-if="!cell.isRunning" class="h-4 w-4" />
          <div v-else class="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-400"></div>
        </button>

        <!-- Add Cell Above -->
        <button
          @click="addCellAbove"
          class="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-200 rounded"
          title="Add cell above"
        >
          <ChevronUpIcon class="h-4 w-4" />
        </button>

        <!-- Add Cell Below -->
        <button
          @click="addCellBelow"
          class="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-200 rounded"
          title="Add cell below"
        >
          <ChevronDownIcon class="h-4 w-4" />
        </button>

        <!-- Delete Cell -->
        <button
          @click="deleteCell"
          class="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded"
          title="Delete cell"
          :disabled="isOnlyCell"
        >
          <XMarkIcon class="h-4 w-4" />
        </button>

        <!-- Split Cell -->
        <button
          @click="splitCell"
          class="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded"
          title="Split cell (Ctrl+Shift+-)"
        >
          <ScissorsIcon class="h-4 w-4" />
        </button>

        <!-- Join Cells -->
        <button
          @click="joinCells"
          class="p-1.5 text-gray-400 hover:text-purple-600 hover:bg-purple-50 rounded"
          title="Join cells (Ctrl+Shift++)"
        >
          <RectangleStackIcon class="h-4 w-4" />
        </button>
      </div>
    </div>

    <!-- Cell Content -->
    <div class="p-2">
      <!-- Code Editor -->
      <div
        ref="cellEditorContainer"
        class="min-h-12 border border-gray-200 rounded"
      ></div>

      <!-- Cell Output / Error -->
      <div v-if="cell.output" class="mt-3">
        <!-- Error accordion (collapsed by default) -->
        <template v-if="outputIsError">
          <button
            type="button"
            @click="isOutputExpanded = !isOutputExpanded"
            :class="[
              'w-full flex items-center justify-between px-3 py-2 rounded border text-sm',
              'transition-colors',
              isOutputExpanded
                ? 'bg-red-100 border-red-300 text-red-900 hover:bg-red-200'
                : 'bg-red-50 border-red-200 text-red-900 hover:bg-red-100'
            ]"
          >
            <span class="font-medium">Executed with errors</span>
            <svg
              :class="['h-4 w-4 transition-transform', isOutputExpanded ? 'rotate-180' : '']"
              xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor"
            >
              <path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 10.94l3.71-3.71a.75.75 0 111.06 1.06l-4.24 4.24a.75.75 0 01-1.06 0L5.25 8.29a.75.75 0 01-.02-1.08z" clip-rule="evenodd" />
            </svg>
          </button>
          <div
            v-show="isOutputExpanded"
            class="mt-2 rounded border border-red-300 bg-red-50 text-red-900 p-3 font-mono text-sm whitespace-pre-wrap overflow-x-auto"
            v-html="renderedOutput"
          ></div>
        </template>

        <!-- Non-error output: collapsible like errors -->
        <template v-else>
          <button
            type="button"
            @click="isOutputExpanded = !isOutputExpanded"
            :class="[
              'w-full flex items-center justify-between px-3 py-2 rounded border text-sm',
              'transition-colors',
              isOutputExpanded
                ? 'bg-green-100 border-green-300 text-green-900 hover:bg-green-200'
                : 'bg-green-50 border-green-200 text-green-900 hover:bg-green-100'
            ]"
          >
            <span class="font-medium">Executed successfully</span>
            <svg
              :class="['h-4 w-4 transition-transform', isOutputExpanded ? 'rotate-180' : '']"
              xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor"
            >
              <path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 10.94l3.71-3.71a.75.75 0 111.06 1.06l-4.24 4.24a.75.75 0 01-1.06 0L5.25 8.29a.75.75 0 01-.02-1.08z" clip-rule="evenodd" />
            </svg>
          </button>
          <div
            v-show="isOutputExpanded"
            class="mt-2 rounded border border-gray-200 bg-gray-50 text-gray-900 p-3 font-mono text-sm whitespace-pre-wrap overflow-x-auto"
            v-html="renderedOutput"
          ></div>
        </template>
      </div>

      <!-- Cell Status -->
      <div class="flex items-center justify-end mt-1">
        <div class="text-xs text-gray-500">
          {{ executionStatusText }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue'
import { useAppStore } from '../../stores/appStore'
import { EditorView, basicSetup } from 'codemirror'
import { EditorState, Compartment } from '@codemirror/state'
import { python } from '@codemirror/lang-python'
import { autocompletion } from '@codemirror/autocomplete'
import { keymap } from '@codemirror/view'
import { searchKeymap } from '@codemirror/search'
import { indentWithTab } from '@codemirror/commands'
import { EditorSelection } from '@codemirror/state'
import { toggleComment } from '@codemirror/commands'
import apiService from '../../services/apiService'
import { toast } from '../../composables/useToast'
import { buildExecutionViewModel } from '../../utils/executionViewModel'

import {
  PlayIcon,
  PlusIcon,
  XMarkIcon,
  ChevronUpIcon,
  ChevronDownIcon,
  ScissorsIcon,
  RectangleStackIcon
} from '@heroicons/vue/24/outline'

const props = defineProps({
  cell: {
    type: Object,
    required: true
  },
  index: {
    type: Number,
    required: true
  },
  totalCells: {
    type: Number,
    required: true
  },
  isActive: {
    type: Boolean,
    default: false
  },
  isSelected: {
    type: Boolean,
    default: false
  }
})

const appStore = useAppStore()
const cellEditorContainer = ref(null)
let cellEditor = null
let readOnlyCompartment = new Compartment()

const isOnlyCell = computed(() => props.totalCells === 1)

// Execution status indicator - using computed for proper reactivity
const executionStatusClass = computed(() => {
  if (props.cell.isRunning) {
    return 'bg-yellow-500 animate-pulse' // Running - yellow with pulse
  } else if (props.cell.output) {
    // Check if output contains error
    if (props.cell.output.includes('❌') || props.cell.output.includes('Error')) {
      return 'bg-red-500' // Error - red
    } else {
      return 'bg-green-500' // Success - green
    }
  } else {
    return 'bg-gray-300' // Not executed - gray
  }
})

const executionStatusTitle = computed(() => {
  if (props.cell.isRunning) {
    return 'Cell is currently running...'
  } else if (props.cell.output) {
    if (props.cell.output.includes('❌') || props.cell.output.includes('Error')) {
      return 'Cell executed with errors'
    } else {
      return 'Cell executed successfully'
    }
  } else {
    return 'Cell has not been executed'
  }
})

const executionStatusText = computed(() => {
  if (props.cell.isRunning) {
    return 'Running...'
  } else if (props.cell.output) {
    if (props.cell.output.includes('❌') || props.cell.output.includes('Error')) {
      return 'Executed with errors'
    } else {
      return 'Executed successfully'
    }
  } else {
    return 'Not executed'
  }
})

// Output rendering with ANSI color support
const outputIsError = computed(() => {
  const out = props.cell.output || ''
  const lower = out.toLowerCase()
  return out.includes('❌') || lower.includes('error') || lower.includes('traceback')
})

// Accordion state for error output
const isOutputExpanded = ref(false)

// Default behavior: collapse when error, expand when non-error
watch(() => props.cell.output, (newOut) => {
  // Collapse by default for both error and non-error outputs; user can expand as needed
  isOutputExpanded.value = false
})

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

function ansiToHtml(input) {
  if (!input) return ''
  const ansiRegex = /\x1b\[((?:\d{1,3};?)*)m/g
  let html = ''
  let lastIndex = 0
  let open = false
  let style = {}

  const colorMap = {
    30: '#000000', 31: '#dc2626', 32: '#16a34a', 33: '#ca8a04', 34: '#2563eb', 35: '#7c3aed', 36: '#0891b2', 37: '#e5e7eb',
    90: '#6b7280', 91: '#ef4444', 92: '#22c55e', 93: '#eab308', 94: '#3b82f6', 95: '#a855f7', 96: '#06b6d4', 97: '#ffffff'
  }
  const bgMap = {
    40: '#111827', 41: '#7f1d1d', 42: '#065f46', 43: '#92400e', 44: '#1e3a8a', 45: '#5b21b6', 46: '#115e59', 47: '#9ca3af',
    100: '#374151', 101: '#991b1b', 102: '#166534', 103: '#92400e', 104: '#1e40af', 105: '#6d28d9', 106: '#0f766e', 107: '#d1d5db'
  }

  function styleString(s) {
    const parts = []
    if (s.color) parts.push(`color: ${s.color}`)
    if (s.backgroundColor) parts.push(`background-color: ${s.backgroundColor}`)
    if (s.bold) parts.push('font-weight: 700')
    if (s.italic) parts.push('font-style: italic')
    if (s.underline) parts.push('text-decoration: underline')
    return parts.join('; ')
  }

  function openSpan() {
    if (!open) {
      const s = styleString(style)
      if (s) {
        html += `<span style="${s}">`
        open = true
      }
    }
  }
  function closeSpan() {
    if (open) {
      html += '</span>'
      open = false
    }
  }

  input.replace(ansiRegex, (match, codesStr, offset) => {
    // text before match
    const text = input.slice(lastIndex, offset)
    html += escapeHtml(text)
    lastIndex = offset + match.length

    // process codes
    const codes = codesStr.split(';').filter(Boolean).map(n => parseInt(n, 10))
    if (codes.length === 0) codes.push(0)

    for (const code of codes) {
      if (code === 0) {
        // reset
        closeSpan()
        style = {}
      } else if (code === 1) {
        style.bold = true
      } else if (code === 3) {
        style.italic = true
      } else if (code === 4) {
        style.underline = true
      } else if (code === 22) {
        style.bold = false
      } else if (code === 23) {
        style.italic = false
      } else if (code === 24) {
        style.underline = false
      } else if (code === 39) {
        delete style.color
      } else if (code === 49) {
        delete style.backgroundColor
      } else if (colorMap[code]) {
        style.color = colorMap[code]
      } else if (bgMap[code]) {
        style.backgroundColor = bgMap[code]
      }
    }

    // after applying codes, reopen span if style active
    if (styleString(style)) {
      openSpan()
    } else {
      closeSpan()
    }
    return ''
  })

  // append remaining tail
  const tail = input.slice(lastIndex)
  html += escapeHtml(tail)
  closeSpan()
  return html
}

const renderedOutput = computed(() => {
  return ansiToHtml(props.cell.output || '')
})

// Extract title from the first line of cell content
const cellTitle = computed(() => {
  const content = props.cell.content || ''
  if (!content) return `Cell ${props.index + 1}`

  const firstLine = content.split('\n')[0].trim()

  // Check if first line matches "# cell <number>: <title>" pattern
  const cellCommentMatch = firstLine.match(/^#\s*cell\s+(\d+):\s*(.+)$/i)
  if (cellCommentMatch) {
    const title = cellCommentMatch[2].trim()
    return title || `Cell ${props.index + 1}`
  }

  return `Cell ${props.index + 1}`
})

// Local editable title state
const titleDraft = ref('')
watch(cellTitle, (val) => { titleDraft.value = val }, { immediate: true })

function saveTitle() {
  updateCellTitle(titleDraft.value)
}

function updateCellTitle(newTitle) {
  const safeTitle = (newTitle || '').trim() || 'Untitled'
  const original = props.cell.content ?? ''
  const lines = original.split('\n')
  const firstLineRaw = lines[0] ?? ''
  const firstLineTrimmed = firstLineRaw.trim()

  const match = firstLineTrimmed.match(/^#\s*cell\s+(\d+):\s*(.+)$/i)
  if (match) {
    // Replace existing title line, preserve original spacing before '#'
    const leading = firstLineRaw.match(/^\s*/)?.[0] ?? ''
    lines[0] = `${leading}# cell ${props.index + 1}: ${safeTitle}`
  } else {
    // Prepend a title line
    lines.unshift(`# cell ${props.index + 1}: ${safeTitle}`)
  }

  const updated = lines.join('\n')
  appStore.updateNotebookCell(props.cell.id, { content: updated })
}

// Clean content by removing the title comment from the first line for display
const cleanCellContent = computed(() => {
  const content = props.cell.content ?? ''
  if (!content) return ''

  const lines = content.split('\n')
  const firstLineRaw = lines[0]
  const firstLine = firstLineRaw.trim()

  // Check if first line is a title comment that should be hidden
  const cellCommentMatch = firstLine.match(/^#\s*cell\s+(\d+):\s*(.+)$/i)
  if (cellCommentMatch) {
    // Remove the first line (title comment) and return the rest (preserve trailing newlines)
    const remainingLines = lines.slice(1)
    return remainingLines.join('\n')
  }

  // If no title comment, return content as is
  return content
})

const emit = defineEmits(['click', 'add-cell-above', 'add-cell-below', 'delete-cell', 'split-cell', 'join-cells', 'toggle-selection'])

// Define keymap with access to component functions
const customKeymap = [
  ...searchKeymap,
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
      if (appStore.isNotebookMode && cellEditor) {
        splitCell()
        return true
      }
      return false
    }
  },
  // Cell join shortcut (Ctrl+Shift++)
  {
    key: 'Mod-Shift-=',
    run: () => {
      if (appStore.isNotebookMode) {
        joinCells()
        return true
      }
      return false
    }
  }
]

onMounted(async () => {
  await nextTick()
  initializeCellEditor()
})

onUnmounted(() => {
  if (cellEditor) {
    cellEditor.destroy()
  }
})

// Watch for content changes from store
watch(() => props.cell.content, (newContent) => {
  if (cellEditor && newContent !== cellEditor.state.doc.toString()) {
    updateCellEditorContent()
  }
})

// Watch for running state changes to update read-only mode
watch(() => props.cell.isRunning, (isRunning) => {
  if (cellEditor) {
    // Use compartment to dynamically update read-only state
    cellEditor.dispatch({
      effects: readOnlyCompartment.reconfigure(EditorState.readOnly.of(isRunning))
    })
  }
})

function initializeCellEditor() {
  if (!cellEditorContainer.value) return

  try {
    const extensions = [
      basicSetup,
      python(),
      autocompletion(),
      keymap.of([indentWithTab]),
      keymap.of(customKeymap),
      EditorView.theme({
        '&': {
          fontSize: '13px',
          height: 'auto'
        },
        '.cm-content': {
          padding: '4px',
          minHeight: '32px'
        },
        '.cm-focused': {
          outline: 'none'
        },
        '.cm-editor': {
          height: 'auto'
        },
        '.cm-scroller': {
          fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace'
        }
      }),
      EditorView.updateListener.of((update) => {
        if (update.docChanged) {
          const editedContent = cellEditor.state.doc.toString()
          // Reconstruct full content with title comment if it exists
          const fullContent = props.cell.content ?? ''
          const firstLineRaw = fullContent.split('\n')[0]
          const firstLineTrimmed = firstLineRaw.trim()
          const cellCommentMatch = firstLineTrimmed.match(/^#\s*cell\s+(\d+):\s*(.+)$/i)

          let contentToSave
          if (cellCommentMatch) {
            // Prepend the original title comment line back to the edited content
            contentToSave = firstLineRaw + '\n' + editedContent
          } else {
            // No title comment, use edited content as is
            contentToSave = editedContent
          }

          appStore.updateNotebookCell(props.cell.id, { content: contentToSave })
        }
      }),
      // Make editor read-only when cell is running (using compartment)
      readOnlyCompartment.of(EditorState.readOnly.of(props.cell.isRunning))
    ]

    const state = EditorState.create({
      doc: cleanCellContent.value,
      extensions
    })

    cellEditor = new EditorView({
      state,
      parent: cellEditorContainer.value
    })

  } catch (error) {
    console.error('Failed to initialize cell editor:', error)
  }
}

function updateCellEditorContent() {
  if (cellEditor) {
    const currentEditorContent = cellEditor.state.doc.toString()
    const newCleanContent = cleanCellContent.value

    if (currentEditorContent !== newCleanContent) {
      const transaction = cellEditor.state.update({
        changes: {
          from: 0,
          to: cellEditor.state.doc.length,
          insert: newCleanContent
        }
      })
      cellEditor.dispatch(transaction)
    }
  }
}


function addCellAbove() {
  emit('add-cell-above', props.index)
}

function addCellBelow() {
  emit('add-cell-below', props.index)
}

function deleteCell() {
  if (props.totalCells > 1) {
    emit('delete-cell', props.cell.id)
  }
}

function splitCell() {
  if (cellEditor) {
    const cursor = cellEditor.state.selection.main.head
    const content = cellEditor.state.doc.toString()
    const beforeCursor = content.substring(0, cursor).trim()
    const afterCursor = content.substring(cursor).trim()

    // Get the title comment from the original cell content
    const fullContent = props.cell.content.trim()
    const firstLine = fullContent.split('\n')[0].trim()
    const cellCommentMatch = firstLine.match(/^#\s*cell\s+(\d+):\s*(.+)$/i)

    let titleComment = ''
    if (cellCommentMatch) {
      titleComment = firstLine
    }

    // If cursor is at the beginning or end, split the cell in half
    if (!beforeCursor && !afterCursor) {
      const midPoint = Math.floor(content.length / 2)
      const beforeContent = content.substring(0, midPoint).trim()
      const afterContent = content.substring(midPoint).trim()

      emit('split-cell', {
        cellId: props.cell.id,
        beforeContent: titleComment ? titleComment + '\n' + beforeContent : beforeContent || '# cell ' + (props.index + 1) + ': Write your Python code here',
        afterContent: afterContent || '# cell ' + (props.index + 2) + ': Write your Python code here'
      })
    } else {
      emit('split-cell', {
        cellId: props.cell.id,
        beforeContent: titleComment ? titleComment + '\n' + beforeCursor : beforeCursor || '# cell ' + (props.index + 1) + ': Write your Python code here',
        afterContent: afterCursor || '# cell ' + (props.index + 2) + ': Write your Python code here'
      })
    }
  }
}

function joinCells() {
  emit('join-cells', props.cell.id)
}

function handleCellClick(event) {
  if (event.ctrlKey || event.metaKey) {
    // Multi-select with Ctrl/Cmd+click
    emit('toggle-selection', props.cell.id)
  } else {
    // Single click - set as active
    emit('click', props.index)
  }
  // Focus the editor to ensure keyboard input works
  if (cellEditor) {
    cellEditor.focus()
  }
}

function handleKeydown(event) {
  if (event.key === 'Enter' && cellEditor) {
    event.preventDefault()
    cellEditor.focus()
    const state = cellEditor.state
    const changes = state.changes([{from: state.selection.main.head, insert: '\n'}])
    cellEditor.dispatch(state.update(changes))
  }
}

async function runCell() {
  if (!cleanCellContent.value.trim()) return

  appStore.updateNotebookCell(props.cell.id, { isRunning: true, output: '' })

  try {
    const code = cleanCellContent.value
    const response = await apiService.executeCode(code)
    const viewModel = buildExecutionViewModel(response)
    appStore.setDataframes(viewModel.dataframes)
    if (viewModel.dataframes.length > 0) {
      appStore.setResultData(viewModel.dataframes[0].data)
    }
    appStore.setFigures(viewModel.figures)
    if (viewModel.figures.length > 0) {
      appStore.setPlotlyFigure(viewModel.figures[0].data)
    }
    appStore.setScalars(viewModel.scalars)
    appStore.updateNotebookCell(props.cell.id, { output: viewModel.output, isRunning: false })

  } catch (error) {
    console.error('Cell execution failed:', error)
    const errData = error.response?.data || {}
    const errorMessage = [
      errData.detail,
      errData.traceback,
      errData.stderr,
      error.message
    ].filter(Boolean).join('\n') || 'Cell execution failed'
    appStore.updateNotebookCell(props.cell.id, {
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
.notebook-cell {
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.notebook-cell:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}
</style>
