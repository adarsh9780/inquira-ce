<template>
  <div class="tool-activity-row" :data-status="toolStatus">
    <p class="tool-activity-action">{{ actionLabel }}</p>
    <p
      class="tool-activity-detail"
      :class="{
        'tool-activity-detail-running': toolStatus === 'running',
        'tool-activity-detail-error': toolStatus === 'error'
      }"
    >
      {{ summaryText }}
      <span v-if="durationLabel" class="tool-activity-duration">{{ durationLabel }}</span>
    </p>

    <p v-if="errorSummary" class="tool-activity-error">
      {{ errorSummary }}
    </p>

    <ToolOutputPreview
      v-if="shouldRenderOutputPreview"
      :activity="activity"
      :collapsed="collapsed"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import ToolOutputPreview from './ToolOutputPreview.vue'
import { toolOutputHasRenderableContent } from '../../utils/toolOutputPreview'

const props = defineProps({
  activity: {
    type: Object,
    required: true,
  },
  collapsed: {
    type: Boolean,
    default: false,
  },
})

const toolName = computed(() => String(props.activity?.tool || '').trim())
const toolLabel = computed(() => toolName.value || 'tool')
const normalizedToolName = computed(() => toolName.value.toLowerCase())
const toolStatus = computed(() => String(props.activity?.status || 'running').trim().toLowerCase())
const toolExplanation = computed(() => truncateText(props.activity?.explanation, 140))
const rawToolArgs = computed(() => {
  const args = props.activity?.args
  return args && typeof args === 'object' ? args : {}
})
const toolArgs = computed(() => {
  const args = { ...rawToolArgs.value }
  delete args.explanation
  return args
})
const durationMs = computed(() => {
  const ms = Number(props.activity?.duration_ms)
  return Number.isFinite(ms) ? ms : null
})
const durationLabel = computed(() => {
  if (durationMs.value === null) return ''
  const seconds = Math.round(durationMs.value / 1000)
  if (seconds < 1) return ''
  if (seconds < 60) return `for ${seconds}s`
  const minutes = Math.floor(seconds / 60)
  const remaining = seconds % 60
  if (remaining === 0) return `for ${minutes}m`
  return `for ${minutes}m ${remaining}s`
})

function truncateText(value, max = 88) {
  const text = String(value || '').trim()
  if (!text) return ''
  if (text.length <= max) return text
  return `${text.slice(0, max - 1)}…`
}

function shortInline(value, max = 60) {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string') return truncateText(value, max)
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  if (Array.isArray(value)) {
    const normalized = value
      .map((entry) => shortInline(entry, 20))
      .filter(Boolean)
    const preview = normalized.slice(0, 3).join(', ')
    if (!preview) return ''
    if (normalized.length > 3) return `${preview} +${normalized.length - 3} more`
    return preview
  }
  if (typeof value === 'object') {
    const keys = Object.keys(value)
    if (!keys.length) return '{}'
    return `${keys[0]}…`
  }
  return truncateText(String(value), max)
}

function listFromArgs(value) {
  if (!Array.isArray(value)) return []
  return value
    .map((entry) => {
      if (typeof entry === 'string') return entry.trim()
      if (entry && typeof entry === 'object') return String(entry.name || '').trim()
      return ''
    })
    .filter(Boolean)
}

function firstText(...values) {
  for (const value of values) {
    const text = truncateText(value, 50)
    if (text) return text
  }
  return ''
}

function summarizeList(values, max = 3) {
  const filtered = values.filter(Boolean)
  if (!filtered.length) return ''
  if (filtered.length <= max) return filtered.join(', ')
  return `${filtered.slice(0, max).join(', ')} +${filtered.length - max} more`
}

function numericArg(value) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

const actionLabel = computed(() => {
  const normalized = normalizedToolName.value
  if (normalized === 'search_schema' || normalized === 'scan_schema_chunks') return 'Searching data context'
  if (normalized === 'sample_data' || normalized === 'sample_data_runtime') return 'Sampling data'
  if (normalized === 'execute_python' || normalized === 'execute_python_runtime') return 'Running generated Python'
  if (normalized === 'validate_result_runtime') return 'Checking result quality'
  if (normalized === 'bash') return 'Running shell command'
  if (normalized === 'pip_install') return 'Installing package'
  return 'Action'
})

const summaryText = computed(() => {
  if (toolExplanation.value) return toolExplanation.value

  const tool = toolLabel.value
  const args = toolArgs.value
  const normalized = normalizedToolName.value
  const table = firstText(args.table_name, args.table, args.dataset_name, args.dataset)
  const columns = [
    ...listFromArgs(args.columns),
    ...listFromArgs(args.column_names),
    ...listFromArgs(args.selected_columns),
  ]

  if (columns.length > 0) {
    const columnText = summarizeList(columns)
    if (table) return `Looking for ${columnText} in ${table} using ${tool} tool`
    return `Looking for ${columnText} using ${tool} tool`
  }

  if (normalized === 'search_schema') {
    const query = firstText(args.query) || summarizeList(listFromArgs(args.queries), 6)
    const output = props.activity?.output
    let count = numericArg(args.match_count)
    if (count === null && output && typeof output === 'object') {
      count = numericArg(output.match_count)
      if (count === null && Array.isArray(output.columns)) {
        count = output.columns.length
      }
    }
    if (query && count !== null) return `Searching schema for "${query}" (${count} matches)`
    if (query) return `Searching schema for "${query}"`
    if (count !== null) return `Searching schema (${count} matches)`
    return 'Searching schema'
  }

  if (normalized === 'sample_data' || normalized === 'sample_data_runtime') {
    const limit = numericArg(args.limit)
    if (table && limit !== null) return `Sampling ${limit} rows from ${table}`
    if (table) return `Sampling rows from ${table}`
    return 'Sampling data'
  }

  if (normalized === 'pip_install') {
    const packages = listFromArgs(args.packages)
    if (packages.length > 0) return `Installing ${summarizeList(packages)} using ${tool} tool`
    return `Installing packages using ${tool} tool`
  }

  if (normalized === 'bash') {
    const isComplete = toolStatus.value !== 'running'
    const command = firstText(args.command)
    const verb = isComplete ? 'Ran' : 'Running'
    if (command) return `${verb} command`
    return `${verb} shell command`
  }

  if (normalized === 'execute_python' || normalized === 'execute_python_runtime') {
    const timeout = numericArg(args.timeout)
    if (timeout !== null) return `Running generated Python (timeout ${timeout}s)`
    return 'Running generated Python'
  }

  if (normalized === 'validate_result_runtime') {
    return 'Checking whether result answers the question'
  }

  const entries = Object.entries(args)
  if (!entries.length) return `Running ${tool} tool`
  const preview = entries
    .slice(0, 2)
    .map(([key, value]) => `${key}=${shortInline(value, 24)}`)
    .filter((entry) => !entry.endsWith('='))
    .join(', ')
  if (!preview) return `Running ${tool} tool`
  return `Running ${tool} with ${preview}`
})

const errorSummary = computed(() => {
  if (toolStatus.value !== 'error') return ''
  const payload = props.activity?.output
  if (payload === null || payload === undefined) return 'Tool failed before returning a result.'
  if (typeof payload === 'string') return payload
  if (payload && typeof payload === 'object') {
    return String(payload.error || payload.stderr || payload.message || 'Tool returned an error.')
  }
  return String(payload)
})

const shouldRenderOutputPreview = computed(() => {
  if (toolStatus.value === 'running') return false
  return toolOutputHasRenderableContent(props.activity)
})
</script>

<style scoped>
.tool-activity-row {
  padding: 0;
}

.tool-activity-action {
  margin: 0;
  font-size: 0.8rem;
  line-height: 1.3;
  letter-spacing: 0.01em;
  color: color-mix(in srgb, var(--color-text-muted) 90%, var(--color-text-main) 10%);
}

.tool-activity-detail {
  margin: 0.1rem 0 0;
  font-size: 0.875rem;
  line-height: 1.58;
  color: color-mix(in srgb, var(--color-text-main) 90%, var(--color-text-muted) 10%);
  word-break: break-word;
}

.tool-activity-detail-running {
  color: var(--color-text-main);
}

.tool-activity-detail-error {
  color: var(--color-danger);
}

.tool-activity-duration {
  color: color-mix(in srgb, var(--color-text-muted) 84%, var(--color-text-main) 16%);
  font-weight: 400;
  margin-left: 0.2rem;
}

.tool-activity-error {
  margin-top: 1px;
  margin-bottom: 0;
  margin-left: 0;
  font-size: 11px;
  line-height: 1.4;
  color: var(--color-danger);
  word-break: break-word;
}
</style>
