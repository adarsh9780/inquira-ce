<template>
  <div class="rounded-xl border p-3 space-y-2" style="border-color: var(--color-border); background-color: var(--color-surface);">
    <div class="flex items-center justify-between gap-2">
      <div class="text-xs font-semibold uppercase tracking-[0.08em]" style="color: var(--color-text-muted);">
        {{ toolLabel }}
      </div>
      <div class="text-xs" style="color: var(--color-text-muted);">
        {{ statusLabel }}
      </div>
    </div>

    <p v-if="argsSummary" class="text-xs break-words" style="color: var(--color-text-muted);">
      {{ argsSummary }}
    </p>

    <TerminalRenderer
      v-if="showTerminal"
      :command="terminalCommand"
      :lines="toolLines"
    />

    <pre
      v-else-if="hasOutput"
      class="text-xs whitespace-pre-wrap rounded-md p-2 max-h-40 overflow-auto"
      style="background: color-mix(in srgb, var(--color-base) 90%, #000 10%); color: var(--color-text-main);"
    >{{ formattedOutput }}</pre>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import TerminalRenderer from './TerminalRenderer.vue'

const props = defineProps({
  activity: {
    type: Object,
    required: true,
  },
})

const toolName = computed(() => String(props.activity?.tool || '').trim())
const toolLabel = computed(() => toolName.value || 'tool')
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
const argsSummary = computed(() => {
  const entries = Object.entries(toolArgs.value)
  if (entries.length === 0) return ''
  return entries
    .slice(0, 4)
    .map(([key, value]) => `${key}: ${typeof value === 'string' ? value : JSON.stringify(value)}`)
    .join(' | ')
})
const toolLines = computed(() => {
  const lines = props.activity?.lines
  return Array.isArray(lines) ? lines.map((line) => String(line || '')) : []
})
const terminalCommand = computed(() => String(toolArgs.value.command || toolName.value))
const showTerminal = computed(() => ['bash', 'pip_install'].includes(toolName.value))
const hasOutput = computed(() => props.activity?.output !== null && props.activity?.output !== undefined)
const formattedOutput = computed(() => {
  const payload = props.activity?.output
  if (payload === null || payload === undefined) return ''
  if (typeof payload === 'string') return payload
  try {
    return JSON.stringify(payload, null, 2)
  } catch (_error) {
    return String(payload)
  }
})
</script>
