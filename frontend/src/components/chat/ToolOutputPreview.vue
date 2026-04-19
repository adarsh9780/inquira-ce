<template>
  <div
    v-if="preview.kind !== 'empty'"
    class="tool-output-preview"
    :data-kind="preview.kind"
    :data-error="Boolean(preview.error)"
    :data-expanded="expanded ? 'true' : 'false'"
  >
    <div class="tool-output-header">
      <button
        type="button"
        class="tool-output-toggle"
        :aria-expanded="expanded ? 'true' : 'false'"
        @click="toggleExpanded"
      >
        <span class="tool-output-caret" aria-hidden="true">›</span>
        <span class="tool-output-label">{{ outputLabel }}</span>
        <span class="tool-output-state">{{ expanded ? 'Hide' : 'Show' }}</span>
      </button>
      <button
        v-if="copyText"
        type="button"
        class="tool-output-copy"
        title="Copy full output"
        @click="copyFullOutput"
      >
        Copy
      </button>
    </div>

    <div v-if="expanded" class="tool-output-body">
      <div v-if="isCodePreview" class="tool-output-code">
        <pre><code :class="`language-${preview.language || 'text'}`" v-html="highlightedCode"></code></pre>
      </div>

      <div v-else-if="preview.kind === 'markdown'" class="tool-output-markdown" v-html="renderedMarkdown"></div>

      <div v-else-if="preview.kind === 'table'" class="tool-output-table-wrap">
        <table class="tool-output-table">
          <thead>
            <tr>
              <th v-for="column in preview.columns" :key="column">{{ column }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, rowIndex) in preview.rows" :key="rowIndex">
              <td v-for="(cell, cellIndex) in row" :key="`${rowIndex}-${cellIndex}`">{{ cell }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else-if="preview.kind === 'json'" class="tool-output-json">
        <div v-if="preview.summary?.length" class="tool-output-json-summary">
          <p v-for="item in preview.summary" :key="item">{{ item }}</p>
        </div>
        <details class="tool-output-json-raw">
          <summary>Raw output</summary>
          <pre>{{ preview.text }}</pre>
        </details>
      </div>

      <pre v-else class="tool-output-logs">{{ preview.text }}</pre>

      <p v-if="preview.truncated" class="tool-output-truncated">Preview truncated. Copy full output for details.</p>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'
import Prism from 'prismjs'
import 'prismjs/components/prism-bash'
import 'prismjs/components/prism-python'
import 'prismjs/components/prism-sql'
import { buildToolOutputPreview } from '../../utils/toolOutputPreview'

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

const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
})

const preview = computed(() => buildToolOutputPreview(props.activity))
const expanded = ref(!props.collapsed)

watch(
  () => props.collapsed,
  (collapsed) => {
    expanded.value = !collapsed
  },
  { immediate: true },
)

const isCodePreview = computed(() => String(preview.value.kind || '').startsWith('code-'))

const outputLabel = computed(() => {
  const kind = String(preview.value.kind || '')
  if (kind === 'code-python') return 'Python'
  if (kind === 'code-sql') return 'SQL'
  if (kind === 'code-bash') return 'Shell'
  if (kind === 'markdown') return 'Output'
  if (kind === 'table') return 'Table preview'
  if (kind === 'json') return 'Structured output'
  return preview.value.error ? 'Error output' : 'Output'
})

const copyText = computed(() => {
  const value = preview.value
  if (!value || value.kind === 'empty') return ''
  if (value.kind === 'table') {
    const rows = [
      value.columns.join('\t'),
      ...value.rows.map((row) => row.map((cell) => String(cell ?? '')).join('\t')),
    ]
    return rows.join('\n')
  }
  return String(value.text || '')
})

const highlightedCode = computed(() => {
  const language = String(preview.value.language || 'text').trim().toLowerCase()
  const text = String(preview.value.text || '')
  const grammar = Prism.languages[language]
  const html = grammar ? Prism.highlight(text, grammar, language) : escapeHtml(text)
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: ['span'],
    ALLOWED_ATTR: ['class'],
  })
})

const renderedMarkdown = computed(() => {
  const html = md.render(String(preview.value.text || ''))
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: [
      'p',
      'strong',
      'em',
      'code',
      'pre',
      'table',
      'thead',
      'tbody',
      'tr',
      'th',
      'td',
      'ul',
      'ol',
      'li',
      'a',
      'br',
    ],
    ALLOWED_ATTR: ['href', 'target', 'rel'],
  })
})

function escapeHtml(text) {
  return String(text || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function toggleExpanded() {
  expanded.value = !expanded.value
}

async function copyFullOutput() {
  if (!copyText.value) return
  try {
    await navigator.clipboard.writeText(copyText.value)
  } catch (error) {
    console.error('Failed to copy tool output:', error)
  }
}
</script>

<style scoped>
.tool-output-preview {
  margin-top: 0.45rem;
  border: 1px solid color-mix(in srgb, var(--color-border) 84%, transparent);
  border-radius: 8px;
  background-color: color-mix(in srgb, var(--color-surface) 78%, var(--color-base));
  overflow: hidden;
}

.tool-output-preview[data-error="true"] {
  border-color: color-mix(in srgb, var(--color-danger) 34%, var(--color-border));
  background-color: color-mix(in srgb, var(--color-danger) 7%, var(--color-base));
}

.tool-output-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.42rem 0.65rem;
  border-bottom: 1px solid color-mix(in srgb, var(--color-border) 70%, transparent);
}

.tool-output-preview[data-expanded="false"] .tool-output-header {
  border-bottom-color: transparent;
}

.tool-output-toggle {
  min-width: 0;
  flex: 1;
  display: inline-flex;
  align-items: center;
  gap: 0.38rem;
  border: 0;
  padding: 0;
  background: transparent;
  color: var(--color-text-muted);
  text-align: left;
  cursor: pointer;
}

.tool-output-toggle:hover {
  color: var(--color-text-main);
}

.tool-output-caret {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 0.7rem;
  height: 0.7rem;
  transform: rotate(90deg);
  transition: transform 130ms ease;
  font-size: 0.9rem;
  line-height: 1;
  color: currentColor;
}

.tool-output-preview[data-expanded="false"] .tool-output-caret {
  transform: rotate(0deg);
}

.tool-output-label {
  font-size: 0.7rem;
  line-height: 1.2;
  color: var(--color-text-muted);
  font-weight: 500;
}

.tool-output-toggle:hover .tool-output-label {
  color: var(--color-text-main);
}

.tool-output-state {
  font-size: 0.68rem;
  line-height: 1.2;
  color: color-mix(in srgb, var(--color-text-muted) 78%, transparent);
}

.tool-output-copy {
  border: 0;
  border-radius: 6px;
  padding: 0.12rem 0.4rem;
  background: transparent;
  color: var(--color-text-muted);
  font-size: 0.7rem;
  cursor: pointer;
}

.tool-output-copy:hover {
  color: var(--color-text-main);
  background-color: color-mix(in srgb, var(--color-border) 56%, transparent);
}

.tool-output-code pre,
.tool-output-logs,
.tool-output-json-raw pre {
  margin: 0;
  padding: 0.65rem;
  max-height: 220px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: var(--font-mono);
  font-size: 0.78rem;
  line-height: 1.55;
  color: var(--color-text-main);
}

.tool-output-code code {
  font-family: inherit;
  font-size: inherit;
}

.tool-output-markdown {
  padding: 0.55rem 0.65rem 0.7rem;
  max-height: 240px;
  overflow: auto;
  font-size: 0.82rem;
  line-height: 1.55;
  color: var(--color-text-main);
}

.tool-output-markdown :deep(table),
.tool-output-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.78rem;
}

.tool-output-markdown :deep(th),
.tool-output-markdown :deep(td),
.tool-output-table th,
.tool-output-table td {
  border-bottom: 1px solid color-mix(in srgb, var(--color-border) 70%, transparent);
  padding: 0.35rem 0.45rem;
  text-align: left;
  vertical-align: top;
}

.tool-output-markdown :deep(th),
.tool-output-table th {
  color: var(--color-text-muted);
  font-weight: 600;
}

.tool-output-table-wrap {
  max-height: 240px;
  overflow: auto;
}

.tool-output-json {
  padding: 0.55rem 0.65rem 0.7rem;
}

.tool-output-json-summary {
  display: grid;
  gap: 0.25rem;
  margin-bottom: 0.4rem;
}

.tool-output-json-summary p {
  margin: 0;
  font-size: 0.78rem;
  line-height: 1.4;
  color: var(--color-text-main);
  word-break: break-word;
}

.tool-output-json-raw summary {
  cursor: pointer;
  color: var(--color-text-muted);
  font-size: 0.75rem;
  user-select: none;
}

.tool-output-json-raw pre {
  margin-top: 0.35rem;
  border-radius: 6px;
  background-color: color-mix(in srgb, var(--color-base) 72%, var(--color-surface));
}

.tool-output-truncated {
  margin: 0;
  padding: 0 0.65rem 0.6rem;
  font-size: 0.72rem;
  line-height: 1.35;
  color: var(--color-text-muted);
}
</style>
