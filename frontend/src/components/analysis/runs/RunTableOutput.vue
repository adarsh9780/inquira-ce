<template>
  <div class="min-w-0" data-run-table>
    <div
      class="run-table-viewport"
      data-run-table-scroll
      role="region"
      aria-label="Scrollable table output"
      tabindex="0"
    >
      <table
        class="run-table-grid"
        role="grid"
        aria-label="Run table output"
        :aria-rowcount="normalized.rowCount"
        :aria-colcount="columns.length"
      >
        <thead>
          <tr>
            <th
              v-for="(column, columnIndex) in columns"
              :key="`${columnIndex}-${column}`"
              :class="{ 'run-table-sticky-column': columnIndex === 0 }"
              scope="col"
            >
              <span :title="column">{{ column }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, rowIndex) in previewRows" :key="rowIndex" :aria-rowindex="rowIndex + 2">
            <td
              v-for="(column, columnIndex) in columns"
              :key="`${rowIndex}-${columnIndex}-${column}`"
              :class="{ 'run-table-sticky-column': columnIndex === 0 }"
              :title="formatCell(row?.[column])"
            >
              <span v-if="row?.[column] === null" class="run-table-null">null</span>
              <span v-else>{{ formatCell(row?.[column]) }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="mt-2 flex items-center justify-between gap-3 text-[11px] tabular-nums" style="color: var(--color-text-muted);">
      <p>{{ rowSummary }}</p>
      <p>{{ columnSummary }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  output: { type: Object, required: true },
})

const normalized = computed(() => {
  const value = props.output?.data ?? props.output
  if (Array.isArray(value)) {
    const rows = value.filter((row) => row && typeof row === 'object' && !Array.isArray(row))
    return { rows, columns: rows[0] ? Object.keys(rows[0]) : [], rowCount: rows.length }
  }
  if (!value || typeof value !== 'object') return { rows: [], columns: [], rowCount: 0 }
  const rawRows = Array.isArray(value.data) ? value.data : []
  const explicitColumns = Array.isArray(value.columns) ? value.columns.map(String) : []
  const rows = rawRows.map((row) => {
    if (row && typeof row === 'object' && !Array.isArray(row)) return row
    if (!Array.isArray(row) || explicitColumns.length === 0) return null
    return Object.fromEntries(explicitColumns.map((column, index) => [column, row[index]]))
  }).filter(Boolean)
  const columns = explicitColumns.length > 0 ? explicitColumns : (rows[0] ? Object.keys(rows[0]) : [])
  return {
    rows,
    columns,
    rowCount: Number.isFinite(Number(value.row_count)) ? Number(value.row_count) : rows.length,
  }
})

const columns = computed(() => normalized.value.columns)
const previewRows = computed(() => normalized.value.rows.slice(0, 100))
const rowSummary = computed(() => {
  const shown = previewRows.value.length
  const total = Math.max(shown, normalized.value.rowCount)
  return shown < total ? `Showing ${shown} of ${total} rows` : `${total} ${total === 1 ? 'row' : 'rows'}`
})
const columnSummary = computed(() => {
  const count = columns.value.length
  return `${count} ${count === 1 ? 'column' : 'columns'}`
})

function formatCell(value) {
  if (value === null) return 'null'
  if (value === undefined) return ''
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean' || typeof value === 'bigint') return String(value)
  try {
    return JSON.stringify(value)
  } catch (_error) {
    return String(value)
  }
}
</script>

<style scoped>
.run-table-viewport {
  max-height: min(36rem, 64vh);
  min-width: 0;
  overflow: auto;
  overscroll-behavior: contain;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-base);
  scrollbar-gutter: stable;
  scrollbar-color: var(--color-border-hover) var(--color-panel-muted);
}

.run-table-viewport:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.run-table-grid {
  width: max-content;
  min-width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  table-layout: fixed;
  color: var(--color-text-main);
  font-size: 12px;
  line-height: 1.4;
  text-align: left;
}

.run-table-grid thead {
  position: sticky;
  top: 0;
  z-index: 20;
}

.run-table-grid th,
.run-table-grid td {
  width: 11rem;
  min-width: 11rem;
  max-width: 22rem;
  height: 32px;
  overflow: hidden;
  padding: 0 10px;
  border-right: 1px solid var(--color-border);
  border-bottom: 1px solid color-mix(in srgb, var(--color-border) 74%, transparent);
  white-space: nowrap;
  text-overflow: ellipsis;
}

.run-table-grid th {
  height: 36px;
  background: var(--color-data-grid-header);
  color: var(--color-text-main);
  font-size: 11px;
  font-weight: 650;
  letter-spacing: 0.01em;
}

.run-table-grid th > span,
.run-table-grid td > span {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
}

.run-table-grid td {
  font-family: var(--font-mono);
  font-size: 11px;
  font-variant-numeric: tabular-nums;
}

.run-table-grid th:last-child,
.run-table-grid td:last-child {
  border-right: 0;
}

.run-table-grid tbody tr:last-child td {
  border-bottom: 0;
}

.run-table-grid tbody tr:nth-child(even) td {
  background: var(--color-data-grid-row-alt);
}

.run-table-grid tbody tr:hover td {
  background: var(--color-data-grid-row-hover);
}

.run-table-grid .run-table-sticky-column {
  position: sticky;
  left: 0;
  z-index: 10;
  box-shadow: 1px 0 0 var(--color-border);
}

.run-table-grid th.run-table-sticky-column {
  z-index: 30;
  background: var(--color-data-grid-header);
}

.run-table-grid tbody tr:nth-child(odd) td.run-table-sticky-column {
  background: var(--color-base);
}

.run-table-grid tbody tr:nth-child(even) td.run-table-sticky-column {
  background: var(--color-data-grid-row-alt);
}

.run-table-grid tbody tr:hover td.run-table-sticky-column {
  background: var(--color-data-grid-row-hover);
}

.run-table-null {
  color: var(--color-text-muted);
  font-style: italic;
}

.run-table-viewport::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}

.run-table-viewport::-webkit-scrollbar-track {
  background: var(--color-panel-muted);
}

.run-table-viewport::-webkit-scrollbar-thumb {
  border: 2px solid var(--color-panel-muted);
  border-radius: 999px;
  background: var(--color-border-hover);
}
</style>
