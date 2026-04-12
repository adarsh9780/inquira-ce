<template>
  <div class="schema-editor h-full flex flex-col relative overflow-hidden">
    <Teleport to="body">
      <!-- Regeneration Overlay -->
      <Transition
        enter-active-class="transition duration-300 ease-out"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition duration-200 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div
          v-if="isRegenerating"
          class="fixed inset-0 z-50 flex items-center justify-center"
          style="background: linear-gradient(135deg, rgba(15, 23, 42, 0.75) 0%, rgba(30, 41, 59, 0.85) 100%); backdrop-filter: blur(8px);"
        >
          <div class="relative overflow-hidden rounded-2xl shadow-2xl border w-full max-w-md mx-4" style="background: linear-gradient(180deg, var(--color-surface) 0%, color-mix(in srgb, var(--color-surface) 95%, var(--color-base)) 100%); border-color: color-mix(in srgb, var(--color-border) 50%, transparent);">
            <!-- Accent line -->
            <div class="absolute top-0 left-0 right-0 h-1" style="background: linear-gradient(90deg, var(--color-accent), color-mix(in srgb, var(--color-accent) 60%, #f97316), var(--color-accent));"></div>
            
            <div class="px-6 py-6">
              <div class="flex items-start justify-between gap-4 mb-5">
                <div>
                  <h3 class="text-base font-semibold tracking-tight" style="color: var(--color-text-main);">Generating Schema</h3>
                  <p class="mt-1.5 text-sm" style="color: var(--color-text-muted);">{{ regenerationStatus }}</p>
                </div>
                <!-- Spinning loader -->
                <div class="relative w-10 h-10 flex-shrink-0">
                  <div class="absolute inset-0 rounded-full border-2" style="border-color: color-mix(in srgb, var(--color-border) 30%, transparent);"></div>
                  <div class="absolute inset-0 rounded-full border-2 border-t-current animate-spin" style="color: var(--color-accent); border-color: color-mix(in srgb, var(--color-accent) 30%, transparent); border-top-color: var(--color-accent);"></div>
                </div>
              </div>

              <div class="mb-4 h-2 w-full overflow-hidden rounded-full" style="background-color: color-mix(in srgb, var(--color-border) 40%, transparent);">
                <div
                  class="h-full rounded-full transition-all duration-500 ease-out"
                  :style="{
                    width: `${regenerationProgress}%`,
                    background: 'linear-gradient(90deg, var(--color-accent), color-mix(in srgb, var(--color-accent) 70%, #f97316))',
                    boxShadow: '0 0 12px color-mix(in srgb, var(--color-accent) 50%, transparent)',
                  }"
                ></div>
              </div>

              <div class="flex items-center justify-between">
                <div class="text-xs font-medium" style="color: var(--color-text-muted);">
                  {{ regenerationProgress }}% complete
                </div>
                <div class="text-xs tabular-nums font-mono" style="color: var(--color-text-muted);">
                  {{ formatElapsedTime(elapsedTime) }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Header -->
    <div class="schema-top-bar relative z-10">
      <div class="flex flex-wrap items-end justify-between gap-3">
        <div class="min-w-0">
          <h2 class="schema-page-title">Schema Editor</h2>
          <p class="schema-page-subtitle">Manage column metadata</p>
        </div>

        <div class="schema-action-bar">
          <div class="schema-dataset-selector w-[240px] max-w-[52vw] min-w-[180px]">
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

          <div class="schema-action-divider" aria-hidden="true"></div>

          <button
            @click="refreshSchema"
            :disabled="schemaLoading || !hasActiveDataset"
            class="schema-ghost-btn"
          >
            Refresh
          </button>
          <button
            @click="regenerateSchema"
            :disabled="schemaLoading || !hasActiveDataset"
            class="schema-ghost-btn"
            title="Regenerate schema with AI descriptions"
          >
            Regenerate
          </button>
          <button
            @click="clearCache"
            class="schema-ghost-btn"
            title="Clear cached schema data"
          >
            Clear Cache
          </button>
          <button
            @click="exportSchema"
            :disabled="schema.length === 0"
            class="schema-ghost-btn"
          >
            Export
          </button>
          <button
            @click="saveSchema"
            :disabled="schemaLoading || !schemaEdited || !hasActiveDataset"
            class="schema-save-btn"
          >
            Save
          </button>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="relative z-10 min-h-0 flex-1 overflow-hidden">
      <!-- Empty State -->
      <div
        v-if="!hasActiveDataset && !schemaLoading"
        class="flex h-full flex-col items-center justify-center py-16 text-center"
      >
          <!-- Schema illustration -->
          <div class="relative mb-6">
            <div class="flex h-20 w-20 items-center justify-center rounded-2xl" style="background: linear-gradient(135deg, color-mix(in srgb, var(--color-surface) 80%, var(--color-base)), color-mix(in srgb, var(--color-surface) 40%, var(--color-base))); border: 1px solid color-mix(in srgb, var(--color-border) 40%, transparent); box-shadow: 0 8px 32px color-mix(in srgb, var(--color-border) 20%, transparent);">
              <svg class="w-10 h-10" style="color: var(--color-text-muted); opacity: 0.5;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 6h16M4 10h16M4 14h16M4 18h16"></path>
              </svg>
            </div>
            <!-- Decorative ring -->
            <div class="absolute -inset-3 rounded-full border border-dashed opacity-30" style="border-color: var(--color-border);"></div>
          </div>
          
          <h3 class="text-lg font-semibold mb-2" style="color: var(--color-text-main);">No Dataset Selected</h3>
          <p class="mt-1 max-w-sm text-sm leading-relaxed" style="color: var(--color-text-muted);">
            Select a dataset from the dropdown above to view and edit schema metadata.
          </p>
      </div>

      <!-- Loading State -->
      <div v-else-if="schemaLoading && !isRegenerating" class="flex h-full flex-col items-center justify-center py-16">
        <div class="relative mb-6">
          <div class="h-16 w-16 rounded-full border-2" style="border-color: color-mix(in srgb, var(--color-border) 20%, transparent);"></div>
          <div class="absolute inset-0 h-16 w-16 rounded-full border-2 border-t-current animate-spin" style="color: var(--color-accent); border-color: color-mix(in srgb, var(--color-accent) 20%, transparent); border-top-color: var(--color-accent);"></div>
        </div>
        <p class="text-sm font-medium" style="color: var(--color-text-muted);">Loading schema...</p>
      </div>

      <!-- Error State -->
      <div v-else-if="schemaError" class="mx-4 mt-4">
        <div class="rounded-xl border px-4 py-3.5" style="border-color: color-mix(in srgb, #ef4444 40%, var(--color-border)); background: linear-gradient(135deg, color-mix(in srgb, #fef2f2 80%, var(--color-base)), color-mix(in srgb, #fef2f2 40%, var(--color-base)));">
          <div class="flex items-start gap-3">
            <svg class="w-5 h-5 mt-0.5 flex-shrink-0" style="color: #dc2626;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
            <p class="text-sm" style="color: #991b1b;">{{ schemaError }}</p>
          </div>
        </div>
      </div>

      <!-- Schema Content -->
      <div v-else-if="hasActiveDataset" class="h-full overflow-auto">
        <div class="px-4 py-4 space-y-4">
          <!-- Warning Banner -->
          <Transition
            enter-active-class="transition duration-300 ease-out"
            enter-from-class="opacity-0 -translate-y-2"
            enter-to-class="opacity-100 translate-y-0"
            leave-active-class="transition duration-200 ease-in"
            leave-from-class="opacity-100 translate-y-0"
            leave-to-class="opacity-0 -translate-y-2"
          >
            <div
              v-if="schemaNeedsDescriptions && !isRegenerating"
              class="rounded-xl border px-4 py-3.5"
              style="border-color: color-mix(in srgb, #f59e0b 40%, var(--color-border)); background: linear-gradient(135deg, color-mix(in srgb, #fffbeb 80%, var(--color-base)), color-mix(in srgb, #fef3c7 40%, var(--color-base)));"
            >
              <div class="flex items-start gap-3">
                <svg class="w-5 h-5 mt-0.5 flex-shrink-0" style="color: #d97706;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                <div>
                  <h4 class="text-sm font-semibold" style="color: #92400e;">Schema Descriptions Not Generated Yet</h4>
                  <p class="mt-0.5 text-sm" style="color: #b45309;">
                    Descriptions are blank. Click <strong>Regenerate</strong> to generate AI descriptions.
                  </p>
                </div>
              </div>
            </div>
          </Transition>

          <!-- Context Section -->
          <div class="schema-context-card">
            <div class="mb-2 flex items-start justify-between gap-3">
              <label class="schema-context-label">Context</label>
              <button
                @click="openEditDialog(-1, 'context')"
                class="schema-context-edit-link"
              >
                <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path>
                </svg>
                Edit
              </button>
            </div>

            <div
              v-if="schemaContext && schemaContext.trim()"
              class="schema-context-body prose prose-sm max-w-none"
            >
              <div v-html="renderedContext"></div>
            </div>
            <div
              v-else
              class="schema-context-empty"
            >
              Click edit to add context for this dataset...
            </div>
          </div>

          <!-- Schema Table -->
          <div class="schema-table-wrap overflow-hidden">
            <table class="schema-table min-w-full">
              <thead>
                <tr class="schema-table-header-row">
                  <th class="schema-row-header-cell" aria-label="Row"></th>
                  <th class="schema-header-cell">Column</th>
                  <th class="schema-header-cell">Description</th>
                  <th class="schema-header-cell">Aliases</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(col, i) in schema"
                  :key="i"
                  class="schema-row group align-top"
                  :class="i % 2 === 0 ? 'schema-row-odd' : 'schema-row-even'"
                >
                  <td class="schema-row-number-cell">
                    {{ i + 1 }}
                  </td>
                  <td class="schema-column-cell">
                    {{ col.name }}
                  </td>
                  <td class="schema-description-cell relative">
                    <div class="min-h-[24px] pr-10">
                      <span
                        v-if="col.description"
                        class="schema-description-text"
                      >{{ col.description }}</span>
                      <span v-else class="schema-description-empty">No description</span>
                    </div>
                    <button
                      @click="openEditDialog(i, 'description')"
                      class="schema-inline-edit-btn absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100"
                      title="Edit description"
                    >
                      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path>
                      </svg>
                    </button>
                  </td>
                  <td class="schema-alias-cell relative">
                    <div class="min-h-[24px] pr-10">
                      <div v-if="col.aliases && col.aliases.length > 0" class="flex flex-wrap gap-1">
                        <span
                          v-for="(alias, ai) in col.aliases"
                          :key="ai"
                          class="schema-alias-tag"
                        >
                          {{ alias }}
                        </span>
                      </div>
                      <span v-else class="schema-description-empty">No aliases</span>
                    </div>
                    <button
                      @click="openEditDialog(i, 'aliases')"
                      class="schema-inline-edit-btn absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100"
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

          <!-- Footer hint -->
          <div class="schema-footer-hint flex items-center justify-center gap-2 py-2">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
            Aliases are search hints for schema lookup. Enter comma-separated values per column.
          </div>
        </div>
      </div>

      <!-- Edit Dialog Modal -->
      <Teleport to="body">
        <Transition
          enter-active-class="transition duration-300 ease-out"
          enter-from-class="opacity-0"
          enter-to-class="opacity-100"
          leave-active-class="transition duration-200 ease-in"
          leave-from-class="opacity-100"
          leave-to-class="opacity-0"
        >
          <div
            v-if="editDialog.isOpen"
            class="fixed inset-0 z-[70] overflow-y-auto"
            aria-labelledby="edit-dialog-title"
            role="dialog"
            aria-modal="true"
          >
            <!-- Backdrop -->
            <div
              class="fixed inset-0 transition-opacity duration-300"
              style="background: linear-gradient(135deg, rgba(15, 23, 42, 0.6) 0%, rgba(30, 41, 59, 0.75) 100%); backdrop-filter: blur(4px);"
              @click="closeEditDialog"
            ></div>

            <div class="flex min-h-full items-center justify-center p-4 text-center sm:p-6">
              <!-- Dialog Panel -->
              <Transition
                enter-active-class="transition duration-300 ease-out"
                enter-from-class="opacity-0 scale-95 translate-y-4"
                enter-to-class="opacity-100 scale-100 translate-y-0"
                leave-active-class="transition duration-200 ease-in"
                leave-from-class="opacity-100 scale-100 translate-y-0"
                leave-to-class="opacity-0 scale-95 translate-y-4"
              >
                <div
                  v-if="editDialog.isOpen"
                  class="relative overflow-hidden rounded-2xl shadow-2xl transition-all sm:my-8 sm:w-full sm:max-w-lg"
                  style="background: linear-gradient(180deg, var(--color-surface) 0%, color-mix(in srgb, var(--color-surface) 95%, var(--color-base)) 100%); border: 1px solid color-mix(in srgb, var(--color-border) 40%, transparent);"
                  @click.stop
                >
                  <!-- Accent gradient top bar -->
                  <div class="absolute top-0 left-0 right-0 h-1" style="background: linear-gradient(90deg, var(--color-accent), color-mix(in srgb, var(--color-accent) 60%, #f97316), var(--color-accent));"></div>
                  
                  <!-- Header -->
                  <div class="px-6 pt-6 pb-5" style="border-bottom: 1px solid color-mix(in srgb, var(--color-border) 30%, transparent);">
                    <div class="flex items-start justify-between gap-4">
                      <div>
                        <h3 class="text-lg font-semibold tracking-tight" id="edit-dialog-title" style="color: var(--color-text-main);">
                          Edit {{ editDialog.field === 'description' ? 'Description' : editDialog.field === 'aliases' ? 'Aliases' : 'Context' }}
                        </h3>
                        <div class="mt-2 inline-flex items-center gap-2 rounded-lg border px-2.5 py-1 text-xs font-medium" style="border-color: color-mix(in srgb, var(--color-border) 40%, transparent); color: var(--color-text-muted); background: color-mix(in srgb, var(--color-base) 50%, transparent);">
                          <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"></path>
                          </svg>
                          {{ editDialog.columnName }}
                        </div>
                      </div>
                      <button
                        @click="closeEditDialog"
                        class="p-2 rounded-xl transition-all duration-200"
                        style="color: var(--color-text-muted);"
                        title="Close"
                      >
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                      </button>
                    </div>
                  </div>

                  <!-- Body -->
                  <div class="px-6 py-5">
                    <div v-if="editDialog.field === 'description'">
                      <label class="mb-2 block text-xs font-medium" style="color: var(--color-text-muted);">Description</label>
                      <textarea
                        v-model="editDialog.value"
                        rows="4"
                        class="w-full resize-y rounded-lg px-3 py-2.5 text-sm leading-relaxed outline-none transition-shadow"
                        style="border: 1px solid color-mix(in srgb, var(--color-border) 60%, transparent); color: var(--color-text-main); background-color: var(--color-base);"
                        placeholder="Enter a description for this column..."
                        autofocus
                      ></textarea>
                    </div>
                    <div v-else-if="editDialog.field === 'aliases'">
                      <label class="mb-2 block text-xs font-medium" style="color: var(--color-text-muted);">Aliases</label>
                      <textarea
                        v-model="editDialog.value"
                        rows="3"
                        class="w-full resize-y rounded-lg px-3 py-2.5 text-sm leading-relaxed outline-none transition-shadow"
                        style="border: 1px solid color-mix(in srgb, var(--color-border) 60%, transparent); color: var(--color-text-main); background-color: var(--color-base);"
                        placeholder="id, identifier, key"
                        autofocus
                      ></textarea>
                    </div>
                    <div v-else-if="editDialog.field === 'context'">
                      <label class="mb-2 block text-xs font-medium" style="color: var(--color-text-muted);">Context Description</label>
                      <textarea
                        v-model="editDialog.value"
                        rows="6"
                        class="w-full resize-y rounded-lg px-3 py-2.5 text-sm leading-relaxed outline-none transition-shadow"
                        style="border: 1px solid color-mix(in srgb, var(--color-border) 60%, transparent); color: var(--color-text-main); background-color: var(--color-base);"
                        placeholder="Example: Daily transaction-level sales data for retail stores. Revenue is in USD. 'channel' means online vs in-store."
                        autofocus
                      ></textarea>
                    </div>
                  </div>

                  <!-- Footer -->
                  <div class="px-6 py-4 flex items-center justify-end gap-3" style="border-top: 1px solid color-mix(in srgb, var(--color-border) 30%, transparent); background: linear-gradient(180deg, color-mix(in srgb, var(--color-base) 40%, transparent) 0%, color-mix(in srgb, var(--color-base) 60%, transparent) 100%);">
                    <button
                      @click="closeEditDialog"
                      class="rounded-xl px-4 py-2.5 text-sm font-medium transition-all duration-200"
                      style="color: var(--color-text-muted); background: transparent;"
                    >
                      Cancel
                    </button>
                    <button
                      @click="saveEditDialog"
                      class="rounded-xl px-5 py-2.5 text-sm font-semibold transition-all duration-200 shadow-sm hover:shadow-md hover:-translate-y-0.5"
                      style="background: linear-gradient(135deg, var(--color-accent), color-mix(in srgb, var(--color-accent) 85%, #f97316)); color: white; box-shadow: 0 2px 8px color-mix(in srgb, var(--color-accent) 30%, transparent);"
                    >
                      Save Changes
                    </button>
                  </div>
                </div>
              </Transition>
            </div>
          </div>
        </Transition>
      </Teleport>
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
  const fallbackTableName = String(selectedDatasetTable.value || appStore.ingestedTableName || '').trim()
  const fallbackSourcePath = String(selectedDatasetPath.value || appStore.dataFilePath || '').trim()
  const options = Array.isArray(datasetOptions.value) ? [...datasetOptions.value] : []

  if (fallbackTableName && !options.some((item) => item.tableName === fallbackTableName)) {
    options.push({
      tableName: fallbackTableName,
      sourcePath: fallbackSourcePath,
    })
  }

  if (options.length === 0) {
    return [{ value: '', label: 'No datasets' }]
  }
  return options.map((item) => ({
    value: item.tableName,
    label: datasetFriendlyName(item.tableName),
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

function datasetFriendlyName(tableName) {
  const raw = String(tableName || '').trim()
  if (!raw) return 'Untitled dataset'
  const withoutHashSuffix = raw.replace(/__\d{6,}(?=__|$)/g, '')
  const compacted = withoutHashSuffix.replace(/_{2,}/g, '_').replace(/^_+|_+$/g, '')
  return compacted || raw
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

function ensureDatasetOption(tableName, sourcePath = '') {
  const normalizedTableName = String(tableName || '').trim()
  if (!normalizedTableName) return null

  const existing = datasetOptions.value.find((item) => item.tableName === normalizedTableName) || null
  if (existing) {
    if (!existing.sourcePath && sourcePath) {
      existing.sourcePath = sourcePath
    }
    return existing
  }

  const fallbackEntry = {
    tableName: normalizedTableName,
    sourcePath: String(sourcePath || '').trim(),
  }
  datasetOptions.value = [...datasetOptions.value, fallbackEntry]
  return fallbackEntry
}

function applyDatasetSelection(tableName, sourcePath = '') {
  const normalized = String(tableName || '').trim()
  if (!normalized) {
    selectedDatasetTable.value = ''
    selectedDatasetPath.value = ''
    return null
  }
  const found = ensureDatasetOption(normalized, sourcePath)
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
  const activePath = String(appStore.dataFilePath || '').trim()
  const keepCurrent = applyDatasetSelection(selectedDatasetTable.value)
  if (keepCurrent) return

  const fromActive = applyDatasetSelection(activeTable)
  if (fromActive) return

  const ensuredActive = ensureDatasetOption(activeTable, activePath)
  if (ensuredActive) {
    applyDatasetSelection(ensuredActive.tableName, ensuredActive.sourcePath)
    return
  }

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

function syncSelectionFromStore() {
  const activeTable = String(appStore.ingestedTableName || '').trim()
  const activePath = String(appStore.dataFilePath || '').trim()
  if (!activeTable) return null
  return applyDatasetSelection(activeTable, activePath)
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
    applyDatasetSelection(newTableName, newDataPath || appStore.dataFilePath || '')
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

watch(
  () => [appStore.ingestedTableName, appStore.dataFilePath],
  ([nextTableName, nextDataPath]) => {
    const normalizedTableName = String(nextTableName || '').trim()
    if (!normalizedTableName || !String(appStore.activeWorkspaceId || '').trim()) return
    applyDatasetSelection(normalizedTableName, String(nextDataPath || '').trim())
  }
)

watch(
  () => appStore.activeTab,
  async (nextTab) => {
    if (nextTab !== 'schema-editor') return

    if (!selectedDatasetTable.value) {
      syncSelectionFromStore()
    }

    if (!selectedDatasetTable.value || schemaLoading.value || schema.value.length > 0) {
      return
    }

    const dataPath = String(selectedDatasetPath.value || appStore.dataFilePath || '').trim()
    if (dataPath) {
      await fetchSchemaDataForPath(dataPath, selectedDatasetTable.value)
      return
    }

    await fetchSchemaData()
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
.schema-editor {
  position: relative;
  background-color: #FAF9F6;
  color: #1A1F2E;
  font-family: 'Ubuntu', sans-serif;
}

.schema-top-bar {
  padding: 12px 16px 10px;
  border-bottom: 1px solid #E5E3DC;
}

.schema-page-title {
  color: #1A1F2E;
  font-size: 15px;
  font-weight: 700;
  line-height: 1.3;
}

.schema-page-subtitle {
  margin-top: 2px;
  color: #6B7280;
  font-size: 13px;
  font-weight: 400;
  line-height: 1.3;
}

.schema-action-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
}

.schema-action-divider {
  width: 1px;
  min-height: 26px;
  background: #E5E3DC;
  margin: 0 4px;
}

.schema-ghost-btn {
  border: 0;
  border-radius: 6px;
  background: transparent;
  padding: 6px 10px;
  color: #1A1F2E;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.3;
  transition: background-color 140ms ease, color 140ms ease;
}

.schema-ghost-btn:hover:not(:disabled) {
  background-color: #EDE9E3;
}

.schema-ghost-btn:disabled {
  opacity: 0.48;
  cursor: not-allowed;
}

.schema-save-btn {
  border: 0;
  border-radius: 6px;
  background: #C96A2E;
  color: #fff;
  padding: 6px 12px;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.3;
  transition: filter 140ms ease, opacity 140ms ease;
}

.schema-save-btn:hover:not(:disabled) {
  filter: brightness(0.95);
}

.schema-save-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.schema-dataset-selector :deep(button) {
  background-color: #FAF9F6;
  border-color: #E5E3DC;
  color: #1A1F2E;
  font-size: 13px;
  font-weight: 500;
}

.schema-dataset-selector :deep(button:focus-visible) {
  box-shadow: 0 0 0 2px color-mix(in srgb, #C96A2E 28%, transparent);
}

.schema-context-card {
  background: #F0EDE6;
  border-left: 3px solid #C96A2E;
  border-radius: 6px;
  padding: 12px 16px;
}

.schema-context-label {
  color: #6B7280;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  line-height: 1.3;
}

.schema-context-edit-link {
  border: 0;
  background: transparent;
  padding: 0;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #C96A2E;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.3;
}

.schema-context-body {
  color: #1A1F2E;
  font-size: 14px;
  font-weight: 400;
  line-height: 1.6;
}

.schema-context-empty {
  color: #6B7280;
  font-size: 14px;
  font-weight: 400;
  font-style: italic;
  line-height: 1.6;
}

.schema-table-wrap {
  background: #FAF9F6;
  border: 0;
  border-radius: 0;
}

.schema-table {
  border-collapse: separate;
  border-spacing: 0;
}

.schema-table-header-row {
  background: #EFEDE8;
}

.schema-row-header-cell {
  width: 32px;
  padding: 9px 6px;
  text-align: right;
  border-bottom: 1px solid #E5E3DC;
}

.schema-header-cell {
  padding: 9px 16px;
  text-align: left;
  border-bottom: 1px solid #E5E3DC;
  color: #6B7280;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  line-height: 1.3;
}

.schema-row {
  transition: background-color 150ms ease;
}

.schema-row-odd {
  background: #FAF9F6;
}

.schema-row-even {
  background: #F5F3EE;
}

.schema-row:hover {
  background: #EDE9E3;
}

.schema-row-number-cell {
  width: 32px;
  padding: 12px 6px;
  text-align: right;
  color: #9CA3AF;
  font-size: 12px;
  font-weight: 400;
  line-height: 1.3;
}

.schema-column-cell {
  padding: 12px 16px;
  vertical-align: top;
  color: #1A1F2E;
  font-family: 'Ubuntu Mono', monospace;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.6;
}

.schema-description-cell,
.schema-alias-cell {
  padding: 12px 16px;
  vertical-align: top;
}

.schema-description-text {
  white-space: pre-wrap;
  color: #1A1F2E;
  font-size: 14px;
  font-weight: 400;
  line-height: 1.6;
}

.schema-description-empty {
  color: #6B7280;
  font-size: 14px;
  font-weight: 400;
  line-height: 1.6;
}

.schema-alias-tag {
  display: inline-flex;
  align-items: center;
  background: #EDE9E3;
  color: #4B4540;
  border: 0;
  border-radius: 4px;
  padding: 2px 8px;
  font-size: 12px;
  font-weight: 400;
  line-height: 1.3;
}

.schema-inline-edit-btn {
  border: 0;
  border-radius: 6px;
  padding: 6px;
  color: #6B7280;
  background: transparent;
  transition: opacity 150ms ease, background-color 150ms ease, color 150ms ease;
}

.schema-inline-edit-btn:hover {
  color: #1A1F2E;
  background: color-mix(in srgb, #1A1F2E 5%, transparent);
}

.schema-footer-hint {
  color: #6B7280;
  font-size: 12px;
  font-weight: 400;
  line-height: 1.3;
  opacity: 0.85;
}

/* Markdown rendered content styling */
.prose {
  color: #1A1F2E;
}

.prose :deep(p) {
  margin: 0;
}

.prose :deep(p:last-child) {
  margin-bottom: 0;
}

.prose :deep(strong) {
  font-weight: 500;
}

.prose :deep(code) {
  font-family: 'Ubuntu Mono', monospace;
  font-size: 13px;
  line-height: 1.6;
  padding: 0.125em 0.375em;
  border-radius: 0.25rem;
  background-color: color-mix(in srgb, #1A1F2E 8%, transparent);
}

.prose :deep(ul),
.prose :deep(ol) {
  margin: 0.35em 0;
  padding-left: 1.5em;
}

.prose :deep(li) {
  margin: 0.2em 0;
}

.prose :deep(a) {
  color: #C96A2E;
  text-decoration: underline;
}

.prose :deep(blockquote) {
  margin: 0.35em 0;
  padding-left: 1em;
  border-left: 3px solid #E5E3DC;
  color: #6B7280;
}

/* Custom scrollbar styling */
.overflow-auto::-webkit-scrollbar,
.overflow-auto::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.overflow-auto::-webkit-scrollbar-track,
.overflow-auto::-webkit-scrollbar-track {
  background: transparent;
}

.overflow-auto::-webkit-scrollbar-thumb,
.overflow-auto::-webkit-scrollbar-thumb {
  background: color-mix(in srgb, #E5E3DC 68%, transparent);
  border-radius: 4px;
}

.overflow-auto::-webkit-scrollbar-thumb:hover,
.overflow-auto::-webkit-scrollbar-thumb:hover {
  background: color-mix(in srgb, #E5E3DC 86%, transparent);
}

/* Focus styles */
textarea:focus,
button:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px color-mix(in srgb, #C96A2E 30%, transparent);
}

/* Animation utilities */
@keyframes pulse-subtle {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

.animate-pulse-subtle {
  animation: pulse-subtle 2s ease-in-out infinite;
}
</style>
