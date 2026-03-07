<template>
  <div class="tool-activity-row" :data-status="toolStatus">
    <div class="tool-activity-main">
      <button
        v-if="hasDetails"
        type="button"
        class="tool-activity-toggle"
        :aria-label="`${summaryText} (${statusLabel})`"
        @click="detailsOpen = !detailsOpen"
      >
        <ChevronRightIcon
          v-if="!detailsOpen"
          class="h-3.5 w-3.5 shrink-0"
          aria-hidden="true"
        />
        <ChevronDownIcon
          v-else
          class="h-3.5 w-3.5 shrink-0"
          aria-hidden="true"
        />
        <span
          class="tool-activity-summary"
          :class="{
            'tool-activity-summary-running': toolStatus === 'running',
            'tool-activity-summary-error': toolStatus === 'error'
          }"
        >
          {{ summaryText }}
          <span v-if="durationLabel" class="tool-activity-duration">{{ durationLabel }}</span>
        </span>
      </button>
      <p
        v-else
        class="tool-activity-summary tool-activity-summary-static"
        :class="{
          'tool-activity-summary-running': toolStatus === 'running',
          'tool-activity-summary-error': toolStatus === 'error'
        }"
        style="display: inline;"
      >
        {{ summaryText }}
      </p>
    </div>

    <p v-if="errorSummary" class="tool-activity-error">
      {{ errorSummary }}
    </p>

    <div v-if="detailsOpen && hasDetails" class="tool-activity-details">
      <div v-if="hasArgs" class="tool-activity-section">
        <p class="tool-activity-label">Tool input</p>
        <pre class="tool-activity-pre">{{ formattedArgs }}</pre>
      </div>

      <div v-if="showTerminal" class="tool-activity-section">
        <TerminalRenderer
          :command="terminalCommand"
          :lines="toolLines"
          :status="toolStatus"
        />
      </div>
      <div v-else-if="hasLines" class="tool-activity-section">
        <p class="tool-activity-label">Execution logs</p>
        <pre
          class="tool-activity-pre tool-activity-log"
        >{{ formattedLines }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ChevronRightIcon, ChevronDownIcon } from '@heroicons/vue/24/outline'
import TerminalRenderer from './TerminalRenderer.vue'

const props = defineProps({
  activity: {
    type: Object,
    required: true,
  },
})

const detailsOpen = ref(false)
const toolName = computed(() => String(props.activity?.tool || '').trim())
const toolLabel = computed(() => toolName.value || 'tool')
const normalizedToolName = computed(() => toolName.value.toLowerCase())
const toolStatus = computed(() => String(props.activity?.status || 'running').trim().toLowerCase())
const statusLabel = computed(() => {
  if (toolStatus.value === 'running') return 'running'
  if (toolStatus.value === 'success') return 'done'
  if (toolStatus.value === 'error') return 'failed'
  return toolStatus.value || 'running'
})
const toolArgs = computed(() => {
  const args = props.activity?.args
  return args && typeof args === 'object' ? args : {}
})
const toolLines = computed(() => {
  const lines = props.activity?.lines
  return Array.isArray(lines) ? lines.map((line) => String(line || '')) : []
})
const hasArgs = computed(() => Object.keys(toolArgs.value).length > 0)
const hasLines = computed(() => toolLines.value.length > 0)
const hasDetails = computed(() => hasArgs.value || hasLines.value || showTerminal.value)
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
const terminalCommand = computed(() => String(toolArgs.value.command || toolName.value))
const showTerminal = computed(() => ['bash', 'pip_install'].includes(normalizedToolName.value))
const formattedLines = computed(() => toolLines.value.join('\n'))
const formattedArgs = computed(() => {
  if (!hasArgs.value) return ''
  return JSON.stringify(toolArgs.value, null, 2)
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

const summaryText = computed(() => {
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

  if (normalized === 'inspect_schema' || normalized === 'input_schema') {
    const count = numericArg(args.column_count)
    if (table && count !== null) return `Checking schema for ${table} (${count} columns) using ${tool} tool`
    if (table) return `Checking schema for ${table} using ${tool} tool`
    return `Checking schema using ${tool} tool`
  }

  if (normalized === 'sample_data') {
    const limit = numericArg(args.limit)
    if (table && limit !== null) return `Sampling ${limit} rows from ${table} using ${tool} tool`
    if (table) return `Sampling rows from ${table} using ${tool} tool`
    return `Sampling data using ${tool} tool`
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

  if (normalized === 'execute_python') {
    const timeout = numericArg(args.timeout)
    if (timeout !== null) return `Running Python validation (timeout ${timeout}s) using ${tool} tool`
    return `Running Python validation using ${tool} tool`
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
</script>

<style scoped>
.tool-activity-row {
  padding: 8px 0;
}

.tool-activity-main {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.tool-activity-toggle {
  border: 0;
  margin: 0;
  padding: 0;
  background: transparent;
  display: inline-flex;
  align-items: flex-start;
  gap: 8px;
  text-align: left;
  cursor: pointer;
  min-width: 0;
  width: 100%;
  color: inherit;
  color: #52525b;
}

.tool-activity-summary {
  display: inline-block;
  font-size: 15px;
  line-height: 1.5;
  color: #52525b;
  word-break: break-word;
}

.tool-activity-summary-static {
  margin: 0;
  min-width: 0;
  flex: 1;
  color: #52525b;
}

.tool-activity-summary-running {
  background-image: linear-gradient(
    110deg,
    #52525b 0%,
    #52525b 32%,
    #a1a1aa 49%,
    #52525b 66%,
    #52525b 100%
  );
  background-size: 220% 100%;
  color: transparent;
  -webkit-background-clip: text;
  background-clip: text;
  animation: tool-running-shine 1.7s linear infinite;
}

.tool-activity-summary-error {
  color: #b91c1c;
}

.tool-activity-duration {
  color: #a1a1aa;
  font-weight: 400;
  margin-left: 2px;
}

.tool-activity-error {
  margin-top: 4px;
  margin-bottom: 0;
  margin-left: 24px;
  font-size: 12px;
  line-height: 1.4;
  color: #b91c1c;
  word-break: break-word;
}

.tool-activity-details {
  margin-top: 7px;
  padding-top: 8px;
  padding-left: 24px;
  border-top: 1px dashed #e4e4e7;
  display: grid;
  gap: 8px;
}

.tool-activity-label {
  margin: 0 0 4px;
  font-size: 11px;
  line-height: 1.3;
  text-transform: none;
  letter-spacing: 0;
  color: #71717a;
}

.tool-activity-pre {
  margin: 0;
  max-height: 240px;
  overflow: auto;
  font-size: 12px;
  line-height: 1.45;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid #e4e4e7;
  white-space: pre-wrap;
  word-break: break-word;
  color: #3f3f46;
  background: #fafafa;
}

.tool-activity-log {
  max-height: 180px;
}

@keyframes tool-running-shine {
  0% {
    background-position: 210% 0;
  }
  100% {
    background-position: -20% 0;
  }
}
</style>
