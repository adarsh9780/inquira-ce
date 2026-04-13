<template>
  <div class="space-y-5">
    <div class="flex items-center gap-0">
      <template v-for="(step, idx) in steps" :key="step.id">
        <div class="flex min-w-0 flex-col items-center">
          <div
            class="flex h-7 w-7 items-center justify-center rounded-full text-xs font-medium"
            :class="circleClass(step.id)"
          >
            <span v-if="step.id < currentStep">✓</span>
            <span v-else>{{ step.id }}</span>
          </div>
          <span class="mt-2 text-center text-[11px] leading-tight text-[var(--color-text-sub)]">{{ step.label }}</span>
        </div>
        <div
          v-if="idx < steps.length - 1"
          class="mx-2 h-px flex-1"
          :class="step.id < currentStep ? 'bg-[var(--color-accent)] opacity-40' : 'bg-[var(--color-border)]'"
        ></div>
      </template>
    </div>

    <div v-if="currentStep === 1" class="space-y-4">
      <div>
        <label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-[var(--color-text-sub)]">Name it</label>
        <input
          :value="wsName"
          type="text"
          placeholder="e.g. IPL 2024 analytics"
          class="w-full rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base-soft)] px-3 py-2 text-sm text-[var(--color-text-main)] outline-none focus:border-[var(--color-accent)] focus:ring-2 focus:ring-[var(--color-accent)]/20"
          @input="emit('update:wsName', $event.target.value)"
        />
      </div>

      <div class="mt-5 flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
        <button
          type="button"
          class="rounded-lg bg-[var(--color-accent)] px-4 py-2 text-sm font-medium text-white transition-all hover:brightness-90 disabled:cursor-not-allowed disabled:opacity-40"
          :disabled="!wsName.trim() || isApplyingDatasetAction"
          @click="emit('update:currentStep', 2)"
        >
          Next
        </button>
      </div>
    </div>

    <div v-else-if="currentStep === 2" class="space-y-4">
      <div
        v-if="isLoadingDatasets"
        class="rounded-lg border border-[var(--color-border)] bg-[var(--color-base-soft)] px-3 py-2 text-xs text-[var(--color-text-muted)]"
      >
        Loading datasets...
      </div>

      <div v-if="datasets.length > 0" class="space-y-2">
        <div
          v-for="dataset in datasets"
          :key="dataset.table_name"
          class="rounded-lg border border-[var(--color-border)] bg-[var(--color-base)] px-3 py-2"
        >
          <div v-if="pendingRemovalTable === dataset.table_name" class="flex items-center justify-between gap-2 text-[13px]">
            <span class="truncate text-[var(--color-text-main)]">
              Remove {{ formatDatasetName(dataset.table_name) }}?
            </span>
            <div class="flex items-center gap-2">
              <button
                type="button"
                class="rounded-lg bg-[var(--color-accent)] px-3 py-1.5 text-xs font-medium text-white transition-all hover:brightness-90"
                :disabled="isApplyingDatasetAction"
                @click="emit('confirm-remove-dataset', dataset)"
              >
                Confirm
              </button>
              <button
                type="button"
                class="rounded-lg border border-[var(--color-border-strong)] px-3 py-1.5 text-xs text-[var(--color-text-sub)] transition-all hover:bg-[var(--color-base-soft)]"
                :disabled="isApplyingDatasetAction"
                @click="emit('cancel-remove-dataset')"
              >
                Cancel
              </button>
            </div>
          </div>

          <div v-else class="flex items-start gap-2.5">
            <div class="mt-0.5 inline-flex h-6 w-6 items-center justify-center rounded-md bg-[var(--color-base-soft)] text-[10px] font-medium text-[var(--color-text-sub)]">
              {{ datasetFileBadge(dataset) }}
            </div>

            <div class="min-w-0 flex-1">
              <p class="truncate text-[13px] font-medium leading-[1.4] text-[var(--color-text-main)]">
                {{ formatDatasetName(dataset.table_name) }}
              </p>
              <p class="truncate text-[12px] font-normal leading-[1.3] text-[var(--color-text-muted)]">
                {{ datasetMetaLine(dataset) }}
              </p>
            </div>

            <div class="flex items-center gap-1">
              <button
                type="button"
                class="rounded-md p-1.5 text-[var(--color-text-muted)] transition-all hover:bg-[var(--color-base-soft)] hover:text-[var(--color-text-main)]"
                title="Refresh from source file"
                :disabled="isApplyingDatasetAction"
                @click="emit('refresh-dataset', dataset)"
              >
                <svg viewBox="0 0 24 24" class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="1.9">
                  <path d="M20 12a8 8 0 1 1-2.34-5.66" />
                  <path d="M20 4v6h-6" />
                </svg>
              </button>

              <button
                type="button"
                class="rounded-md p-1.5 text-[var(--color-text-muted)] transition-all hover:bg-[var(--color-base-soft)] hover:text-[var(--color-danger)]"
                title="Remove dataset from workspace"
                :disabled="isApplyingDatasetAction"
                @click="emit('request-remove-dataset', dataset)"
              >
                <svg viewBox="0 0 24 24" class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="1.9">
                  <path d="M6 6l12 12M18 6L6 18" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        <button
          type="button"
          class="flex w-full items-center justify-center gap-1 rounded-lg border border-dashed border-[var(--color-border-strong)] px-3 py-2 text-sm text-[var(--color-text-sub)] transition-colors hover:border-[var(--color-accent)] hover:bg-[var(--color-accent-soft)]"
          :disabled="isApplyingDatasetAction"
          @click="emit('toggle-compact-dropzone')"
        >
          <span class="text-[var(--color-accent)]">+</span>
          <span>Add another dataset</span>
        </button>
      </div>

      <div
        v-if="datasets.length === 0 || showCompactDropzone"
        class="cursor-pointer rounded-lg border-2 border-dashed border-[var(--color-border-strong)] p-7 text-center transition-colors hover:border-[var(--color-accent)] hover:bg-[var(--color-accent-soft)]"
        @click="emit('add-dataset')"
      >
        <div class="text-2xl">📁</div>
        <p class="mt-2 text-sm font-medium text-[var(--color-text-main)]">Choose data file</p>
        <p class="mt-1 text-xs text-[var(--color-text-muted)]">Your files stay local on this device.</p>
        <div class="mt-3 flex flex-wrap justify-center gap-2">
          <span class="rounded-full bg-[var(--color-base-muted)] px-2.5 py-1 text-[11px] text-[var(--color-text-sub)]">CSV</span>
          <span class="rounded-full bg-[var(--color-base-muted)] px-2.5 py-1 text-[11px] text-[var(--color-text-sub)]">Parquet</span>
          <span class="rounded-full bg-[var(--color-base-muted)] px-2.5 py-1 text-[11px] text-[var(--color-text-sub)]">XLSX</span>
          <span class="rounded-full bg-[var(--color-base-muted)] px-2.5 py-1 text-[11px] text-[var(--color-text-sub)]">JSON</span>
        </div>
      </div>

      <div class="mt-5 flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
        <template v-if="isDatasetManagementMode">
          <button
            type="button"
            class="rounded-lg bg-[var(--color-accent)] px-4 py-2 text-sm font-medium text-white transition-all hover:brightness-90 disabled:cursor-not-allowed disabled:opacity-40"
            :disabled="isApplyingDatasetAction"
            @click="emit('done')"
          >
            Done
          </button>
        </template>

        <template v-else>
          <button
            type="button"
            class="rounded-lg border border-[var(--color-border-strong)] px-4 py-2 text-sm text-[var(--color-text-sub)] transition-all hover:bg-[var(--color-base-soft)] font-medium"
            :disabled="isApplyingDatasetAction"
            @click="emit('update:currentStep', 1)"
          >
            Back
          </button>
          <button
            type="button"
            class="rounded-lg bg-[var(--color-accent)] px-4 py-2 text-sm font-medium text-white transition-all hover:brightness-90 disabled:cursor-not-allowed disabled:opacity-40"
            :disabled="!fileSelected || isApplyingDatasetAction"
            @click="emit('update:currentStep', 3)"
          >
            Next
          </button>
        </template>
      </div>
    </div>

    <div v-else-if="currentStep === 3" class="space-y-4">
      <div>
        <label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-[var(--color-text-sub)]">
          Data context
          <span class="ml-1 rounded-full bg-[var(--color-base-muted)] px-2 py-0.5 text-[10px] normal-case tracking-normal text-[var(--color-text-muted)]">Optional</span>
        </label>
        <textarea
          v-model="dataContext"
          rows="4"
          placeholder="Add business context so analyses are more accurate."
          class="w-full rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base-soft)] px-3 py-2 text-sm text-[var(--color-text-main)] outline-none focus:border-[var(--color-accent)] focus:ring-2 focus:ring-[var(--color-accent)]/20"
        ></textarea>
      </div>

      <div class="rounded-lg border border-[var(--color-accent-border)] bg-[var(--color-accent-soft)] p-3 text-xs leading-relaxed text-[var(--color-text-sub)]">
        Context helps the assistant interpret column intent, business terms, and metric definitions before generating charts and summaries.
      </div>

      <label class="inline-flex cursor-pointer items-start gap-2 text-sm text-[var(--color-text-sub)]">
        <input
          v-model="schemaPrivacy"
          type="checkbox"
          class="mt-0.5"
        />
        <span>Allow sample values in schema prompts for higher-quality field descriptions.</span>
      </label>

      <div class="mt-5 flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
        <button
          type="button"
          class="rounded-lg border border-[var(--color-border-strong)] px-4 py-2 text-sm text-[var(--color-text-sub)] transition-all hover:bg-[var(--color-base-soft)] font-medium"
          @click="emit('update:currentStep', 2)"
        >
          Back
        </button>
        <button
          type="button"
          class="rounded-lg bg-[var(--color-accent)] px-4 py-2 text-sm font-medium text-white transition-all hover:brightness-90"
          @click="emit('trigger-save')"
        >
          Create workspace
        </button>
      </div>
    </div>

    <div v-else class="space-y-4">
      <p class="text-sm text-[var(--color-text-sub)]">Saving workspace setup</p>
      <ul class="space-y-2">
        <li v-for="(item, idx) in saveTasks" :key="item" class="flex items-center gap-2 text-sm text-[var(--color-text-main)]">
          <span v-if="idx + 1 < savingStep" class="text-[var(--color-success)]">✓</span>
          <span
            v-else-if="idx + 1 === savingStep"
            class="h-3 w-3 animate-spin rounded-full border-2 border-[var(--color-accent)] border-t-transparent"
          ></span>
          <span v-else class="text-[var(--color-text-muted)]">○</span>
          <span>{{ item }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  currentStep: {
    type: Number,
    required: true,
  },
  wsName: {
    type: String,
    required: true,
  },
  fileSelected: {
    type: Boolean,
    required: true,
  },
  savingStep: {
    type: Number,
    required: true,
  },
  isDatasetManagementMode: {
    type: Boolean,
    default: false,
  },
  datasets: {
    type: Array,
    default: () => [],
  },
  datasetColumnCounts: {
    type: Object,
    default: () => ({}),
  },
  datasetFileSizes: {
    type: Object,
    default: () => ({}),
  },
  pendingRemovalTable: {
    type: String,
    default: '',
  },
  showCompactDropzone: {
    type: Boolean,
    default: false,
  },
  isLoadingDatasets: {
    type: Boolean,
    default: false,
  },
  isApplyingDatasetAction: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits([
  'update:currentStep',
  'update:wsName',
  'update:fileSelected',
  'trigger-save',
  'add-dataset',
  'toggle-compact-dropzone',
  'refresh-dataset',
  'request-remove-dataset',
  'confirm-remove-dataset',
  'cancel-remove-dataset',
  'done',
])

const dataContext = ref('')
const schemaPrivacy = ref(false)

const steps = [
  { id: 1, label: 'Name' },
  { id: 2, label: 'Data' },
  { id: 3, label: 'Context' },
  { id: 4, label: 'Saving' },
]

const saveTasks = [
  'Creating workspace record',
  'Preparing ingestion queue',
  'Extracting schema metadata',
  'Finalizing local cache',
]

const currentStep = computed(() => props.currentStep)
const wsName = computed(() => props.wsName)
const fileSelected = computed(() => props.fileSelected)
const savingStep = computed(() => props.savingStep)
const datasets = computed(() => props.datasets)
const pendingRemovalTable = computed(() => String(props.pendingRemovalTable || '').trim())

function circleClass(stepId) {
  if (stepId < currentStep.value) {
    return 'bg-[var(--color-accent)] text-white'
  }
  if (stepId === currentStep.value) {
    return 'border-2 border-[var(--color-accent)] bg-[var(--color-accent-soft)] text-[var(--color-accent)]'
  }
  return 'bg-[var(--color-base-muted)] text-[var(--color-text-muted)]'
}

function formatDatasetName(tableName) {
  const raw = String(tableName || '').trim()
  if (!raw) return 'Untitled dataset'
  const hashSegmentIndex = raw.search(/_[0-9a-f]{6,}(?=_|$)/i)
  const withoutHashSuffix = hashSegmentIndex >= 0 ? raw.slice(0, hashSegmentIndex) : raw
  const compacted = withoutHashSuffix.replace(/_{2,}/g, '_').replace(/^_+|_+$/g, '')
  if (compacted) return compacted
  const firstToken = raw.split('_')[0]?.trim()
  return firstToken || 'Untitled dataset'
}

function datasetFileBadge(dataset) {
  const fileType = String(dataset?.file_type || '').trim().toLowerCase()
  if (fileType === 'parquet') return 'PQ'
  if (fileType === 'xlsx' || fileType === 'xls') return 'XL'
  if (fileType === 'json') return 'JS'
  if (fileType === 'tsv') return 'TS'
  return 'CSV'
}

function datasetMetaLine(dataset) {
  const rowCount = Number(dataset?.row_count)
  const columnCount = Number(props.datasetColumnCounts?.[dataset?.table_name])
  const fileBytes = Number(props.datasetFileSizes?.[dataset?.table_name])

  const rowLabel = Number.isFinite(rowCount) && rowCount >= 0
    ? `${rowCount.toLocaleString()} rows`
    : '— rows'
  const columnLabel = Number.isFinite(columnCount) && columnCount >= 0
    ? `${columnCount.toLocaleString()} cols`
    : '— cols'
  const sizeLabel = Number.isFinite(fileBytes) && fileBytes > 0
    ? formatBytes(fileBytes)
    : '—'
  const refreshedLabel = `refreshed ${formatRelativeTime(dataset?.updated_at)}`

  return `${rowLabel} · ${columnLabel} · ${sizeLabel} · ${refreshedLabel}`
}

function formatBytes(value) {
  const bytes = Math.max(0, Number(value || 0))
  if (!Number.isFinite(bytes) || bytes <= 0) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatRelativeTime(value) {
  const ts = Date.parse(String(value || ''))
  if (!Number.isFinite(ts)) return 'just now'
  const diffMs = Date.now() - ts
  const diffSeconds = Math.max(1, Math.floor(diffMs / 1000))
  if (diffSeconds < 60) return `${diffSeconds}s ago`
  const diffMinutes = Math.floor(diffSeconds / 60)
  if (diffMinutes < 60) return `${diffMinutes}m ago`
  const diffHours = Math.floor(diffMinutes / 60)
  if (diffHours < 24) return `${diffHours}h ago`
  const diffDays = Math.floor(diffHours / 24)
  return `${diffDays}d ago`
}
</script>
