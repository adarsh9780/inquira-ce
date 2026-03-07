<template>
  <div class="shell-card">
    <div class="shell-header">
      <span class="shell-badge">Shell</span>
      <button
        v-if="hasOutput"
        type="button"
        class="shell-copy-btn"
        aria-label="Copy output"
        title="Copy output"
        @click="copyOutput"
      >
        <svg class="shell-copy-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <rect x="9" y="9" width="13" height="13" rx="2"></rect>
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
        </svg>
      </button>
    </div>

    <div class="shell-body">
      <pre class="shell-command"><code v-html="highlightedCommand"></code></pre>
      <div v-if="hasOutput" class="shell-output">{{ renderedOutput }}</div>
      <div v-else class="shell-no-output">No output</div>
    </div>

    <div v-if="resolvedStatus !== 'running'" class="shell-footer">
      <span v-if="resolvedStatus === 'success'" class="shell-status shell-status-success">
        <svg class="shell-status-icon" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path fill-rule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clip-rule="evenodd" />
        </svg>
        Success
      </span>
      <span v-else-if="resolvedStatus === 'error'" class="shell-status shell-status-error">
        <svg class="shell-status-icon" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path fill-rule="evenodd" d="M4.28 3.22a.75.75 0 00-1.06 1.06L8.94 10l-5.72 5.72a.75.75 0 101.06 1.06L10 11.06l5.72 5.72a.75.75 0 101.06-1.06L11.06 10l5.72-5.72a.75.75 0 00-1.06-1.06L10 8.94 4.28 3.22z" clip-rule="evenodd" />
        </svg>
        Failed
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import Prism from 'prismjs'
import 'prismjs/components/prism-bash'

const props = defineProps({
  command: {
    type: String,
    default: '',
  },
  lines: {
    type: Array,
    default: () => [],
  },
  status: {
    type: String,
    default: 'running',
  },
})

const commandLine = computed(() => `$ ${String(props.command || '').trim()}`)
const highlightedCommand = computed(() => {
  const raw = commandLine.value
  const grammar = Prism.languages.bash
  if (grammar) {
    return Prism.highlight(raw, grammar, 'bash')
  }
  return raw
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
})

const renderedOutput = computed(() => {
  const rows = Array.isArray(props.lines) ? props.lines : []
  return rows.map((line) => String(line || '')).join('\n')
})

const hasOutput = computed(() => {
  const rows = Array.isArray(props.lines) ? props.lines : []
  return rows.length > 0 && rows.some((line) => String(line || '').trim() !== '')
})

const resolvedStatus = computed(() => {
  const s = String(props.status || 'running').trim().toLowerCase()
  if (s === 'success' || s === 'done') return 'success'
  if (s === 'error' || s === 'failed') return 'error'
  return 'running'
})

async function copyOutput() {
  const text = renderedOutput.value
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
  } catch (error) {
    console.error('Failed to copy terminal output:', error)
  }
}
</script>

<style scoped>
.shell-card {
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid #e4e4e7;
  background: #fafafa;
}

.shell-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
}

.shell-badge {
  display: inline-block;
  font-size: 11px;
  font-weight: 600;
  line-height: 1;
  padding: 3px 7px;
  border-radius: 4px;
  background-color: color-mix(in srgb, var(--color-text-main, #3f3f46) 8%, transparent);
  color: var(--color-text-main, #3f3f46);
}

.shell-copy-btn {
  border: 0;
  margin: 0;
  padding: 4px;
  background: transparent;
  color: #a1a1aa;
  cursor: pointer;
  border-radius: 4px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: color 0.15s ease, background-color 0.15s ease;
}

.shell-copy-btn:hover {
  color: #52525b;
  background-color: #e4e4e7;
}

.shell-copy-icon {
  width: 14px;
  height: 14px;
}

.shell-body {
  padding: 8px 12px 10px;
}

.shell-command {
  margin: 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12.5px;
  line-height: 1.5;
  color: #3f3f46;
  white-space: pre-wrap;
  word-break: break-word;
}

.shell-command code {
  font-family: inherit;
  font-size: inherit;
}

.shell-output {
  margin-top: 8px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  line-height: 1.45;
  color: #71717a;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 180px;
  overflow: auto;
}

.shell-no-output {
  margin-top: 6px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  line-height: 1.45;
  color: #a1a1aa;
  font-style: italic;
}

.shell-footer {
  display: flex;
  justify-content: flex-end;
  padding: 4px 10px 6px;
}

.shell-status {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 12px;
  font-weight: 500;
  line-height: 1;
}

.shell-status-icon {
  width: 13px;
  height: 13px;
}

.shell-status-success {
  color: #16a34a;
}

.shell-status-error {
  color: #dc2626;
}
</style>
