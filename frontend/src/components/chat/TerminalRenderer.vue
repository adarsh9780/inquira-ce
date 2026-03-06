<template>
  <div class="terminal-shell">
    <div class="terminal-head">{{ commandLine }}</div>
    <pre class="terminal-body">{{ renderedOutput }}</pre>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  command: {
    type: String,
    default: '',
  },
  lines: {
    type: Array,
    default: () => [],
  },
})

const commandLine = computed(() => `$ ${String(props.command || '').trim()}`)
const renderedOutput = computed(() => {
  const rows = Array.isArray(props.lines) ? props.lines : []
  return rows.map((line) => String(line || '')).join('\n')
})
</script>

<style scoped>
.terminal-shell {
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid #1f2937;
  background: #0b1220;
}

.terminal-head {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  padding: 8px 10px;
  color: #93c5fd;
  background: #111827;
  border-bottom: 1px solid #1f2937;
}

.terminal-body {
  margin: 0;
  max-height: 180px;
  overflow: auto;
  padding: 10px;
  white-space: pre-wrap;
  word-break: break-word;
  color: #d1fae5;
  font-size: 12px;
  line-height: 1.45;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
</style>
