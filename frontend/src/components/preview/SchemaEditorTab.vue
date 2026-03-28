<template>
  <div class="h-full flex flex-col relative overflow-hidden">
    <Teleport to="body">
      <div
        v-if="isRegenerating"
        class="fixed inset-0 z-50 flex items-center justify-center backdrop-blur-sm"
        style="background-color: color-mix(in srgb, var(--color-text-main) 26%, transparent);"
      >
        <div
          class="w-full max-w-md rounded-xl border px-5 py-4 shadow-xl"
          style="background-color: var(--color-surface); border-color: var(--color-border);"
        >
          <div class="mb-3 flex items-start justify-between gap-3">
            <div>
              <h3 class="text-sm font-semibold" style="color: var(--color-text-main);">Generating Schema</h3>
              <p class="mt-0.5 text-xs" style="color: var(--color-text-muted);">{{ regenerationStatus }}</p>
            </div>
            <div class="h-5 w-5 animate-spin rounded-full border-2 border-transparent border-t-current" style="color: var(--color-accent);"></div>
          </div>

          <div class="mb-2 h-2 w-full rounded-full" style="background-color: color-mix(in srgb, var(--color-border) 45%, transparent);">
            <div
              class="h-2 rounded-full transition-all duration-300"
              :style="{
                width: `${regenerationProgress}%`,
                backgroundColor: 'var(--color-accent)',
              }"
            ></div>
          </div>

          <div class="text-right text-[11px] tabular-nums" style="color: var(--color-text-muted);">
            {{ formatElapsedTime(elapsedTime) }}
          </div>
        </div>
      </div>
    </Teleport>

    <div class="mb-3 flex flex-wrap items-center justify-between gap-3">
      <div class="flex min-w-0 flex-wrap items-center gap-2">
        <div class="text-sm font-semibold" style="color: var(--color-text-main);">Schema Editor</div>
        <div class="w-[220px] max-w-[46vw] min-w-[170px]">
          <HeaderDropdown
            v-model="selectedDatasetTable"
            :options="datasetDropdownOptions"
            placeholder="Select dataset"
            aria-label="Select dataset for schema editor"
            :fit-to-longest-label="true"
            :min-chars="12"
            :max-chars="34"
            max-width-class="w-full"
            @update:model-value="handleDatasetSelection"
          />
        </div>
      </div>

      <div class="flex flex-wrap items-center justify-end gap-2">
        <button
          @click="refreshSchema"
          :disabled="schemaLoading || !hasActiveDataset"
          class="inline-flex items-center rounded-md border px-3 py-1.5 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60"
          style="border-color: var(--color-border); color: var(--color-text-main);"
        >
          Refresh
        </button>
        <button
          @click="regenerateSchema"
          :disabled="schemaLoading || !hasActiveDataset"
          class="inline-flex items-center rounded-md border px-3 py-1.5 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60"
          style="border-color: var(--color-border); color: var(--color-text-main);"
          title="Regenerate schema with AI descriptions"
        >
          Regenerate
        </button>
        <button
          @click="clearCache"
          class="inline-flex items-center rounded-md border px-3 py-1.5 text-xs font-medium transition-colors"
          style="border-color: var(--color-border); color: var(--color-text-main);"
        >
          Clear Cache
        </button>
        <button
          @click="exportSchema"
          :disabled="schema.length === 0"
          class="inline-flex items-center rounded-md border px-3 py-1.5 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60"
          style="border-color: var(--color-border); color: var(--color-text-main);"
        >
          Export
        </button>
        <button
          @click="saveSchema"
          :disabled="schemaLoading || !schemaEdited || !hasActiveDataset"
          class="inline-flex items-center rounded-md px-3 py-1.5 text-xs font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-60"
          style="background-color: var(--color-accent); color: white;"
        >
          Save
        </button>
      </div>
    </div>

    <div
      class="min-h-0 flex-1 overflow-auto rounded-lg border p-3"
      style="background-color: var(--color-base); border-color: var(--color-border);"
    >
      <div
        v-if="!hasActiveDataset && !schemaLoading"
        class="flex h-full flex-col items-center justify-center py-12 text-center"
      >
        <div class="mb-3 h-12 w-12 rounded-full border" style="border-color: var(--color-border); background-color: color-mix(in srgb, var(--color-surface) 65%, var(--color-base));"></div>
        <h3 class="text-sm font-semibold" style="color: var(--color-text-main);">No Dataset Selected</h3>
        <p class="mt-1 max-w-xs text-xs" style="color: var(--color-text-muted);">
          Select a dataset from the dropdown above to view and edit schema for any table directly from this tab.
        </p>
      </div>

      <div v-else-if="schemaLoading && !isRegenerating" class="text-xs" style="color: var(--color-text-muted);">
        Loading schema...
      </div>

      <div v-else-if="schemaError" class="rounded-md border px-3 py-2 text-xs" style="border-color: color-mix(in srgb, #fca5a5 70%, var(--color-border)); color: #b42318; background-color: color-mix(in srgb, #fef2f2 75%, var(--color-base));">
        {{ schemaError }}
      </div>

      <div v-else-if="hasActiveDataset" class="space-y-4">
        <div
          v-if="schemaNeedsDescriptions && !isRegenerating"
          class="rounded-lg border px-3 py-2"
          style="border-color: color-mix(in srgb, #facc15 55%, var(--color-border)); background-color: color-mix(in srgb, #fefce8 70%, var(--color-base));"
        >
          <h4 class="text-xs font-semibold" style="color: #854d0e;">Schema Descriptions Not Generated Yet</h4>
          <p class="mt-0.5 text-xs" style="color: #a16207;">
            Descriptions are blank. Click <strong>Regenerate</strong> to generate AI descriptions.
          </p>
        </div>

        <div class="pb-2">
          <div class="mb-1 flex items-center justify-between">
            <label class="text-[11px] font-semibold uppercase tracking-[0.08em]" style="color: var(--color-text-muted);">LLM Context Hint (Recommended)</label>
            <button
              @click="openEditDialog(-1, 'context')"
              class="opacity-60 hover:opacity-100 p-1 rounded transition-opacity duration-150"
              style="color: var(--color-text-muted);"
              title="Edit context"
            >
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path>
              </svg>
            </button>
          </div>
          <p class="mb-2 text-xs" style="color: var(--color-text-muted);">
            Briefly describe business meaning, domain terms, and how this dataset should be interpreted. This helps the LLM generate better analysis.
          </p>
          <div
            v-if="schemaContext && schemaContext.trim()"
            class="rounded-lg px-4 py-3"
            style="background-color: color-mix(in srgb, var(--color-surface) 60%, var(--color-base)); border: 1px solid color-mix(in srgb, var(--color-border) 50%, transparent);"
          >
            <div class="text-sm leading-relaxed prose prose-sm max-w-none" style="color: var(--color-text-main);" v-html="renderedContext"></div>
          </div>
          <div
            v-else
            class="rounded-lg px-4 py-3 italic text-sm"
            style="color: var(--color-text-muted); background-color: color-mix(in srgb, var(--color-surface) 60%, var(--color-base)); border: 1px dashed color-mix(in srgb, var(--color-border) 50%, transparent);"
          >
            Click the edit icon above to add context for this dataset...
          </div>
        </div>

        <div class="overflow-x-auto rounded-lg" style="border: 1px solid color-mix(in srgb, var(--color-border) 60%, transparent);">
          <table class="min-w-full table-fixed">
            <thead style="background-color: color-mix(in srgb, var(--color-surface) 82%, var(--color-base));">
              <tr>
                <th class="w-[22%] px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.08em]" style="color: var(--color-text-muted); border-bottom: 1px solid color-mix(in srgb, var(--color-border) 50%, transparent);">Column</th>
                <th class="w-[48%] px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.08em]" style="color: var(--color-text-muted); border-bottom: 1px solid color-mix(in srgb, var(--color-border) 50%, transparent);">Description</th>
                <th class="w-[30%] px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.08em]" style="color: var(--color-text-muted); border-bottom: 1px solid color-mix(in srgb, var(--color-border) 50%, transparent);">Aliases</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(col, i) in schema"
                :key="i"
                class="group align-top transition-colors duration-150"
                style="border-bottom: 1px solid color-mix(in srgb, var(--color-border) 40%, transparent);"
              >
                <td class="px-4 py-3">
                  <span class="text-sm font-medium" style="color: var(--color-text-main);">{{ col.name }}</span>
                </td>
                <td class="px-4 py-3 relative">
                  <div class="min-h-[20px] pr-8">
                    <span
                      v-if="col.description"
                      class="text-sm leading-relaxed"
                      style="color: var(--color-text-main); white-space: pre-wrap;"
                    >{{ col.description }}</span>
                    <span v-else class="text-sm italic" style="color: var(--color-text-muted);">No description</span>
                  </div>
                  <button
                    @click="openEditDialog(i, 'description')"
                    class="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 p-1.5 rounded-md transition-all duration-150"
                    style="color: var(--color-text-muted);"
                    title="Edit description"
                  >
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path>
                    </svg>
                  </button>
                </td>
                <td class="px-4 py-3 relative">
                  <div class="min-h-[20px] pr-8">
                    <span
                      v-if="col.aliases && col.aliases.length > 0"
                      class="text-sm leading-relaxed"
                      style="color: var(--color-text-main); white-space: pre-wrap;"
                    >{{ formatAliasesForDisplay(col.aliases) }}</span>
                    <span v-else class="text-sm italic" style="color: var(--color-text-muted);">No aliases</span>
                  </div>
                  <button
                    @click="openEditDialog(i, 'aliases')"
                    class="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 p-1.5 rounded-md transition-all duration-150"
                    style="color: var(--color-text-muted);"
                    title="Edit aliases"
                  >
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path>
                    </svg>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Edit Dialog Modal -->
        <Teleport to="body">
          <div
            v-if="editDialog.isOpen"
            class="fixed inset-0 z-[70] overflow-y-auto"
            aria-labelledby="edit-dialog-title"
            role="dialog"
            aria-modal="true"
          >
            <div
              class="fixed inset-0 transition-opacity"
              style="background-color: color-mix(in srgb, var(--color-text-main) 30%, transparent);"
              @click="closeEditDialog"
            ></div>

            <div class="flex min-h-full items-center justify-center p-4 text-center sm:p-0">
              <div
                class="relative overflow-hidden rounded-xl shadow-2xl transition-all sm:my-8 sm:w-full sm:max-w-lg"
                style="background-color: var(--color-surface);"
                @click.stop
              >
                <div class="px-6 py-5" style="border-bottom: 1px solid color-mix(in srgb, var(--color-border) 60%, transparent);">
                  <div class="flex items-center justify-between">
                    <div>
                      <h3 class="text-base font-semibold" id="edit-dialog-title" style="color: var(--color-text-main);">
                        Edit {{ editDialog.field === 'description' ? 'Description' : 'Aliases' }}
                      </h3>
                      <p class="mt-1 text-xs" style="color: var(--color-text-muted);">
                        Column: <span class="font-medium">{{ editDialog.columnName }}</span>
                      </p>
                    </div>
                    <button
                      @click="closeEditDialog"
                      class="p-1.5 rounded-lg transition-colors"
                      style="color: var(--color-text-muted);"
                    >
                      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                      </svg>
                    </button>
                  </div>
                </div>

                <div class="px-6 py-5">
                  <div v-if="editDialog.field === 'description'">
                    <label class="mb-2 block text-xs font-medium" style="color: var(--color-text-muted);">Description</label>
                    <textarea
                      v-model="editDialog.value"
                      rows="4"
                      class="w-full resize-y rounded-lg px-3 py-2.5 text-sm leading-relaxed outline-none transition-shadow"
                      style="border: 1px solid color-mix(in srgb, var(--color-border) 60%, transparent); color: var(--color-text-main); background-color: var(--color-base);"
                      placeholder="Enter a description for this column..."
                    ></textarea>
                    <p class="mt-2 text-[11px]" style="color: var(--color-text-muted);">
                      Describe the business meaning, format, and any relevant details about this column.
                    </p>
                  </div>
                  <div v-else-if="editDialog.field === 'aliases'">
                    <label class="mb-2 block text-xs font-medium" style="color: var(--color-text-muted);">Aliases</label>
                    <textarea
                      v-model="editDialog.value"
                      rows="3"
                      class="w-full resize-y rounded-lg px-3 py-2.5 text-sm leading-relaxed outline-none transition-shadow"
                      style="border: 1px solid color-mix(in srgb, var(--color-border) 60%, transparent); color: var(--color-text-main); background-color: var(--color-base);"
                      placeholder="Comma-separated aliases (e.g., id, identifier, key)"
                    ></textarea>
                    <p class="mt-2 text-[11px]" style="color: var(--color-text-muted);">
                      Search hints for schema lookup. Enter comma-separated values.
                    </p>
                  </div>
                  <div v-else-if="editDialog.field === 'context'">
                    <label class="mb-2 block text-xs font-medium" style="color: var(--color-text-muted);">Context Description</label>
                    <textarea
                      v-model="editDialog.value"
                      rows="6"
                      class="w-full resize-y rounded-lg px-3 py-2.5 text-sm leading-relaxed outline-none transition-shadow font-mono"
                      style="border: 1px solid color-mix(in srgb, var(--color-border) 60%, transparent); color: var(--color-text-main); background-color: var(--color-base);"
                      placeholder="Example: Daily transaction-level sales data for retail stores. Revenue is in USD. 'channel' means online vs in-store."
                    ></textarea>
                    <p class="mt-2 text-[11px]" style="color: var(--color-text-muted);">
                      Supports markdown formatting. Describe the business meaning, domain terms, and how this dataset should be interpreted.
                    </p>
                  </div>
                </div>

                <div class="px-6 py-4 flex items-center justify-end gap-3" style="border-top: 1px solid color-mix(in srgb, var(--color-border) 60%, transparent); background-color: var(--color-base);">
                  <button
                    @click="closeEditDialog"
                    class="rounded-lg px-4 py-2 text-sm font-medium transition-colors"
                    style="color: var(--color-text-muted); background-color: transparent;"
                  >
                    Cancel
                  </button>
                  <button
                    @click="saveEditDialog"
                    class="rounded-lg px-4 py-2 text-sm font-semibold transition-colors"
                    style="background-color: var(--color-accent); color: white;"
                  >
                    Save Changes
                  </button>
                </div>
              </div>
            </div>
          </div>
        </Teleport>
        <p class="text-[11px]" style="color: var(--color-text-muted);">
          Aliases are search hints for schema lookup. Enter comma-separated values per column.
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { previewService } from '../../services/previewService'
import { apiService } from '../../services/apiService'
import { useAppStore } from '../../stores/appStore'
import { toast } from '../../composables/useToast'
import HeaderDropdown from '../ui/HeaderDropdown.vue'
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({ breaks: true, linkify: true })

const appStore = useAppStore()

const schema = ref([])
const schemaContext = ref('')
const schemaLoading = ref(false)
const schemaError = ref('')
const schemaEdited = ref(false)
const isRegenerating = ref(false)
const datasetOptions = ref([])
const selectedDatasetTable = ref('')
const selectedDatasetPath = ref('')

// Edit dialog state
const editDialog = ref({
  isOpen: false,
  index: -1,
  field: '', // 'description', 'aliases', or 'context'
  columnName: '',
  value: ''
})

// Computed property for rendering context as markdown
const renderedContext = computed(() => {
  if (!schemaContext.value || schemaContext.value.trim() === '') return ''
  return md.render(schemaContext.value)
})

const hasActiveDataset = computed(() => selectedDatasetTable.value.trim() !== '')

const datasetDropdownOptions = computed(() => {
  if (!Array.isArray(datasetOptions.value) || datasetOptions.value.length === 0) {
    return [{ value: '', label: 'No datasets' }]
  }
  return datasetOptions.value.map((item) => ({
    value: item.tableName,
    label: item.tableName,
    key: item.tableName,
  }))
})

const schemaNeedsDescriptions = computed(() => {
  if (!schema.value || schema.value.length === 0) return false
  const allEmpty = schema.value.every(col => !col.description || col.description.trim() === '')
  const emptyContext = !schemaContext.value || schemaContext.value.trim() === ''
  return allEmpty && emptyContext
})

const regenerationStatus = ref('Initializing...')
const regenerationProgress = ref(0)
const elapsedTime = ref(0)
let timerInterval = null

function startTimer() {
  elapsedTime.value = 0
  timerInterval = setInterval(() => {
    elapsedTime.value += 100
  }, 100)
}

function stopTimer() {
  if (timerInterval) {
    clearInterval(timerInterval)
    timerInterval = null
  }
}

function formatElapsedTime(ms) {
  const seconds = Math.floor(ms / 1000)
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  if (minutes > 0) {
    return `${minutes}m ${remainingSeconds}s`
  }
  return `${remainingSeconds}s`
}

function normalizeDatasetEntries(items) {
  return (Array.isArray(items) ? items : [])
    .map((item) => {
      const tableName = String(item?.table_name || '').trim()
      const sourcePath = String(item?.source_path || item?.file_path || '').trim()
      if (!tableName) return null
      return { tableName, sourcePath }
    })
    .filter(Boolean)
}

function extractWorkspaceTableNames(columns) {
  const seen = new Set()
  const tables = []

  ;(Array.isArray(columns) ? columns : []).forEach((column) => {
    const tableName = String(column?.table_name || '').trim()
    const tableKey = tableName.toLowerCase()
    if (!tableName || seen.has(tableKey)) return
    seen.add(tableKey)
    tables.push(tableName)
  })

  return tables
}

function buildSchemaDatasetEntries(catalogItems, workspaceColumns) {
  const runtimeTables = extractWorkspaceTableNames(workspaceColumns)
  const catalogByTable = new Map(
    normalizeDatasetEntries(catalogItems).map((item) => [item.tableName.toLowerCase(), item])
  )
  const mergedEntries = []
  const seen = new Set()

  runtimeTables.forEach((tableName) => {
    const catalogEntry = catalogByTable.get(tableName.toLowerCase())
    const resolved = catalogEntry || { tableName, sourcePath: '' }
    const key = resolved.tableName.toLowerCase()
    if (seen.has(key)) return
    seen.add(key)
    mergedEntries.push(resolved)
  })

  normalizeDatasetEntries(catalogItems).forEach((item) => {
    const key = item.tableName.toLowerCase()
    if (seen.has(key)) return
    seen.add(key)
    mergedEntries.push(item)
  })

  return mergedEntries
}

function normalizeAliasList(value) {
  const source = Array.isArray(value)
    ? value
    : (typeof value === 'string' ? value.split(',') : [])
  const seen = new Set()
  const normalized = []
  source.forEach((item) => {
    const alias = String(item || '').trim()
    if (!alias) return
    const aliasKey = alias.toLowerCase()
    if (seen.has(aliasKey)) return
    seen.add(aliasKey)
    normalized.push(alias)
  })
  return normalized
}

function formatAliasesForInput(value) {
  return normalizeAliasList(value).join(', ')
}

function formatAliasesForDisplay(value) {
  const list = normalizeAliasList(value)
  return list.length > 0 ? list.join(', ') : ''
}

function openEditDialog(index, field) {
  if (field === 'context') {
    editDialog.value = {
      isOpen: true,
      index: -1,
      field: 'context',
      columnName: 'LLM Context Hint',
      value: schemaContext.value || ''
    }
    return
  }
  const col = schema.value[index]
  if (!col) return
  editDialog.value = {
    isOpen: true,
    index,
    field,
    columnName: col.name,
    value: field === 'description'
      ? (col.description || '')
      : formatAliasesForInput(col.aliases)
  }
}

function closeEditDialog() {
  editDialog.value.isOpen = false
}

function saveEditDialog() {
  const { index, field, value } = editDialog.value
  
  if (field === 'context') {
    schemaContext.value = value
    schemaEdited.value = true
    closeEditDialog()
    return
  }
  
  if (index < 0 || !schema.value[index]) return
  
  if (field === 'description') {
    updateSchemaDescription(index, value)
  } else if (field === 'aliases') {
    updateSchemaAliases(index, value)
  }
  
  closeEditDialog()
}

function normalizeSchemaColumns(columns) {
  return (Array.isArray(columns) ? columns : []).map((col) => ({
    ...col,
    aliases: normalizeAliasList(col?.aliases),
  }))
}

function getSelectedDatasetEntry() {
  const tableName = String(selectedDatasetTable.value || '').trim()
  if (!tableName) return null
  return datasetOptions.value.find((item) => item.tableName === tableName) || null
}

function applyDatasetSelection(tableName) {
  const normalized = String(tableName || '').trim()
  if (!normalized) {
    selectedDatasetTable.value = ''
    selectedDatasetPath.value = ''
    return null
  }
  const found = datasetOptions.value.find((item) => item.tableName === normalized) || null
  if (!found) return null
  selectedDatasetTable.value = found.tableName
  selectedDatasetPath.value = found.sourcePath
  return found
}

async function loadSchemaDatasets() {
  const workspaceId = String(appStore.activeWorkspaceId || '').trim()
  if (!workspaceId) {
    datasetOptions.value = []
    selectedDatasetTable.value = ''
    selectedDatasetPath.value = ''
    return
  }

  try {
    const [datasetResponse, columnsResponse] = await Promise.all([
      apiService.v1ListDatasets(workspaceId).catch(() => ({ datasets: [] })),
      apiService.getWorkspaceColumns(workspaceId).catch(() => ({ columns: [] }))
    ])
    datasetOptions.value = buildSchemaDatasetEntries(
      datasetResponse?.datasets || [],
      columnsResponse?.columns || []
    )
  } catch (error) {
    datasetOptions.value = []
  }

  if (datasetOptions.value.length === 0) {
    selectedDatasetTable.value = ''
    selectedDatasetPath.value = ''
    return
  }

  const activeTable = String(appStore.ingestedTableName || '').trim()
  const keepCurrent = applyDatasetSelection(selectedDatasetTable.value)
  if (keepCurrent) return

  const fromActive = applyDatasetSelection(activeTable)
  if (fromActive) return

  applyDatasetSelection(datasetOptions.value[0].tableName)
}

async function fetchSchemaData(forceRefresh = false) {
  const selected = getSelectedDatasetEntry()
  if (!selected || schemaLoading.value) return false
  schemaLoading.value = true
  schemaError.value = ''
  schema.value = []
  try {
    const existingSchema = await previewService.loadSchema(
      selected.sourcePath,
      forceRefresh,
      selected.tableName
    )
    if (existingSchema && existingSchema.columns) {
      schema.value = normalizeSchemaColumns(existingSchema.columns)
      schemaContext.value = existingSchema.context || ''
      schemaEdited.value = false
      return true
    } else {
      schemaError.value = 'Schema has no columns. Try clicking Refresh.'
      return false
    }
  } catch (e) {
    schemaError.value = `Failed to load schema: ${e?.message || 'Unknown error'}`
    return false
  } finally {
    schemaLoading.value = false
  }
}

async function fetchSchemaDataForPath(dataPath, tableNameOverride = null) {
  if (schemaLoading.value || !dataPath) return false
  schemaLoading.value = true
  schemaError.value = ''
  schema.value = []
  try {
    const tableName = (tableNameOverride || selectedDatasetTable.value || appStore.ingestedTableName || '').trim()
    if (tableName) {
      applyDatasetSelection(tableName)
    }
    const existingSchema = await previewService.loadSchema(
      dataPath,
      true,
      tableName
    )
    if (existingSchema && existingSchema.columns) {
      schema.value = normalizeSchemaColumns(existingSchema.columns)
      schemaContext.value = existingSchema.context || ''
      schemaEdited.value = false
      return true
    } else {
      schemaError.value = 'Schema has no columns yet. Click Regenerate to create descriptions manually.'
      return false
    }
  } catch (loadError) {
    if (loadError?.status === 422 || loadError?.response?.status === 422) {
      schemaError.value = 'Schema is not available yet. Click Regenerate to create it manually.'
      return false
    }
    schemaError.value = `Failed to load schema: ${loadError?.message || 'Unknown error'}`
    return false
  } finally {
    schemaLoading.value = false
  }
}

function updateSchemaDescription(index, newDescription) {
  if (schema.value[index]) {
    schema.value[index].description = newDescription
    schemaEdited.value = true
  }
}

function updateSchemaAliases(index, aliasText) {
  if (schema.value[index]) {
    schema.value[index].aliases = normalizeAliasList(aliasText)
    schemaEdited.value = true
  }
}

async function saveSchema() {
  const workspaceId = String(appStore.activeWorkspaceId || '').trim()
  const tableName = String(selectedDatasetTable.value || appStore.ingestedTableName || '').trim()
  const dataPath = String(selectedDatasetPath.value || appStore.dataFilePath || '').trim()

  try {
    if (workspaceId && tableName) {
      await apiService.v1SaveDatasetSchema(workspaceId, tableName, {
        context: schemaContext.value || '',
        columns: normalizeSchemaColumns(schema.value),
      })
    } else if (dataPath) {
      await apiService.saveSchema(dataPath, schemaContext.value || null, normalizeSchemaColumns(schema.value))
    } else {
      schemaError.value = 'Please select a dataset first.'
      toast.info('Select a dataset first')
      return
    }
    schemaEdited.value = false
    toast.success('Schema saved', tableName ? `Saved schema for ${tableName}.` : 'Schema changes were saved.')
  } catch (e) {
    schemaError.value = 'Failed to save schema'
    toast.error('Schema save failed', e?.message || 'Unable to save schema changes.')
  }
}

async function refreshSchema() {
  if (!hasActiveDataset.value) {
    toast.info('Select a dataset first')
    return
  }
  const ok = await fetchSchemaData(true)
  if (ok) {
    toast.success('Schema refreshed', `Reloaded ${selectedDatasetTable.value}.`)
  } else {
    toast.error('Schema refresh failed', schemaError.value || 'Unable to refresh schema.')
  }
}

async function regenerateSchema() {
  if (!hasActiveDataset.value) {
    toast.info('Select a dataset first')
    return
  }
  const settings = await previewService.getSettings()
  const dataPath = selectedDatasetPath.value || settings?.data_path || appStore.dataFilePath || ''
  const tableName = selectedDatasetTable.value || appStore.ingestedTableName || null
  const ok = await regenerateSchemaForPath(dataPath, tableName)
  if (ok) {
    toast.success('Schema regenerated', tableName ? `Generated descriptions for ${tableName}.` : 'Generated schema descriptions.')
  } else {
    toast.error('Schema regeneration failed', schemaError.value || 'Unable to regenerate schema.')
  }
}

async function regenerateSchemaForPath(dataPath, tableName = null, options = {}) {
  if (schemaLoading.value && options?.allowWhileLoading !== true) return false
  schemaLoading.value = true
  schemaError.value = ''
  isRegenerating.value = true
  regenerationStatus.value = 'Initializing...'
  regenerationProgress.value = 0
  startTimer()

  try {
    regenerationStatus.value = 'Loading dataset context...'
    regenerationProgress.value = 10
    const saveTableName = (tableName || selectedDatasetTable.value || appStore.ingestedTableName || '').trim()
    const normalizedPath = (dataPath || '').trim()
    if (!normalizedPath && !(saveTableName && appStore.activeWorkspaceId)) {
      schemaError.value = 'Please configure your data file path in settings first.'
      return false
    }

    regenerationStatus.value = 'Analyzing data columns with AI...'
    regenerationProgress.value = 30

    const generatedSchema = (saveTableName && appStore.activeWorkspaceId)
      ? await apiService.v1RegenerateDatasetSchema(appStore.activeWorkspaceId, saveTableName, {
          context: schemaContext.value || ''
        })
      : await apiService.generateSchema(normalizedPath, schemaContext.value || null, true)

    if (generatedSchema && generatedSchema.columns) {
      regenerationStatus.value = `Saving ${generatedSchema.columns.length} column descriptions...`
      regenerationProgress.value = 80

      if (!saveTableName || !appStore.activeWorkspaceId) {
        await apiService.saveSchema(
          normalizedPath,
          generatedSchema.context || null,
          generatedSchema.columns
        )
      }

      regenerationStatus.value = 'Finalizing...'
      regenerationProgress.value = 95
      previewService.clearSchemaCache()
      schema.value = normalizeSchemaColumns(generatedSchema.columns)
      schemaContext.value = generatedSchema.context || ''
      schemaEdited.value = false
      regenerationProgress.value = 100
      regenerationStatus.value = `Generated ${generatedSchema.columns.length} descriptions`

      await new Promise(resolve => setTimeout(resolve, 500))
      return true
    } else {
      schemaError.value = 'Failed to generate schema. Please try again.'
      return false
    }
  } catch (error) {
    const status = error?.response?.status || error?.status
    const detail = error?.response?.data?.detail || error?.data?.detail || error?.message || 'Unknown error'
    schemaError.value = `Failed to regenerate schema: ${detail}`
    if (status === 401) {
      schemaError.value = 'Failed to regenerate schema: please log in again (session expired).'
    }
    return false
  } finally {
    stopTimer()
    schemaLoading.value = false
    isRegenerating.value = false
  }
}

async function handleDatasetSelection(value) {
  const selected = applyDatasetSelection(value)
  schemaEdited.value = false
  schema.value = []
  schemaContext.value = ''
  schemaError.value = ''
  previewService.clearSchemaCache()

  if (!selected) return
  await fetchSchemaData()
}

async function handleDatasetSwitch(event) {
  const newDataPath = event?.detail?.dataPath
  const newTableName = event?.detail?.tableName

  schemaEdited.value = false
  schema.value = []
  schemaContext.value = ''
  schemaError.value = ''
  previewService.clearSchemaCache()

  // Dataset uploads can happen outside this tab while keeping the same workspace.
  // Reloading catalog options first prevents the schema dropdown from lagging
  // behind newly ingested tables until users manually switch tabs/reopen views.
  await loadSchemaDatasets()

  if (event?.detail === null) {
    if (selectedDatasetTable.value) {
      await fetchSchemaData()
    }
    return
  }

  if (newTableName) {
    applyDatasetSelection(newTableName)
  }
  if (newDataPath) {
    selectedDatasetPath.value = newDataPath
    if (newTableName) {
      appStore.setIngestedTableName(newTableName)
    }
    await fetchSchemaDataForPath(newDataPath, newTableName || selectedDatasetTable.value || null)
    return
  }

  if (selectedDatasetTable.value) {
    await fetchSchemaData()
  }
}

onMounted(async () => {
  await loadSchemaDatasets()
  if (selectedDatasetTable.value) {
    await fetchSchemaData()
  }
  window.addEventListener('dataset-switched', handleDatasetSwitch)
})

onUnmounted(() => {
  stopTimer()
  window.removeEventListener('dataset-switched', handleDatasetSwitch)
})

watch(
  () => appStore.activeWorkspaceId,
  async () => {
    schemaEdited.value = false
    schema.value = []
    schemaContext.value = ''
    schemaError.value = ''
    await loadSchemaDatasets()
    if (selectedDatasetTable.value) {
      await fetchSchemaData()
    }
  }
)

function clearCache() {
  try {
    previewService.clearSchemaCache()
    toast.info('Schema cache cleared')
  } catch (_e) {
    toast.error('Cache clear failed', 'Unable to clear schema cache.')
  }
}

async function persistExportJsonFile(defaultFileName, payloadBytes) {
  if (window.__TAURI_INTERNALS__) {
    const { save } = await import('@tauri-apps/plugin-dialog')
    const savePath = await save({
      defaultPath: defaultFileName,
      filters: [{ name: 'JSON File', extensions: ['json'] }]
    })
    if (!savePath) return false
    const { writeFile } = await import('@tauri-apps/plugin-fs')
    await writeFile(savePath, payloadBytes)
    return true
  }

  if (typeof window.showSaveFilePicker === 'function') {
    try {
      const handle = await window.showSaveFilePicker({
        suggestedName: defaultFileName,
        types: [{ description: 'JSON File', accept: { 'application/json': ['.json'] } }]
      })
      const writable = await handle.createWritable()
      await writable.write(payloadBytes)
      await writable.close()
      return true
    } catch (error) {
      if (error?.name === 'AbortError') return false
      throw error
    }
  }

  const blob = new Blob([payloadBytes], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.setAttribute('href', url)
  link.setAttribute('download', defaultFileName)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  return true
}

async function exportSchema() {
  try {
    if (!schema.value || schema.value.length === 0) {
      toast.info('Nothing to export', 'Load a schema first.')
      return
    }
    const payload = {
      table_name: selectedDatasetTable.value || '',
      context: schemaContext.value || '',
      columns: normalizeSchemaColumns(schema.value),
    }
    const filename = `${selectedDatasetTable.value || 'schema'}.json`
    const bytes = new TextEncoder().encode(JSON.stringify(payload, null, 2))
    const exported = await persistExportJsonFile(filename, bytes)
    if (!exported) {
      toast.info('Export canceled')
      return
    }
    toast.success('Schema exported', `${filename} saved.`)
  } catch (_e) {
    toast.error('Export failed', 'Unable to export schema file.')
  }
}
</script>

<style scoped>
/* Markdown rendered content styling */
.prose {
  color: var(--color-text-main);
}

.prose :deep(p) {
  margin: 0 0 0.5em 0;
}

.prose :deep(p:last-child) {
  margin-bottom: 0;
}

.prose :deep(strong) {
  font-weight: 600;
}

.prose :deep(code) {
  font-family: var(--font-mono);
  font-size: 0.875em;
  padding: 0.125em 0.375em;
  border-radius: 0.25rem;
  background-color: color-mix(in srgb, var(--color-text-main) 8%, transparent);
}

.prose :deep(ul),
.prose :deep(ol) {
  margin: 0.5em 0;
  padding-left: 1.5em;
}

.prose :deep(li) {
  margin: 0.25em 0;
}

.prose :deep(a) {
  color: var(--color-accent);
  text-decoration: underline;
}

.prose :deep(blockquote) {
  margin: 0.5em 0;
  padding-left: 1em;
  border-left: 3px solid var(--color-border);
  color: var(--color-text-muted);
}
</style>
