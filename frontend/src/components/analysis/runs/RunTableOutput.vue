<template>
  <div class="min-w-0" data-run-table>
    <div class="max-h-72 overflow-auto border-y" style="border-color: var(--color-border);">
      <table class="w-full min-w-max border-collapse text-left text-xs">
        <thead class="sticky top-0 z-10" style="background-color: var(--color-panel-muted); color: var(--color-text-sub);">
          <tr>
            <th
              v-for="column in columns"
              :key="column"
              class="border-b px-3 py-2 font-semibold"
              style="border-color: var(--color-border);"
            >
              {{ column }}
            </th>
          </tr>
        </thead>
        <tbody class="divide-y" style="border-color: color-mix(in srgb, var(--color-border) 72%, transparent);">
          <tr v-for="(row, rowIndex) in previewRows" :key="rowIndex">
            <td
              v-for="column in columns"
              :key="`${rowIndex}-${column}`"
              class="max-w-72 px-3 py-2 align-top font-mono"
              style="color: var(--color-text-main);"
            >
              <span class="block max-h-20 overflow-hidden whitespace-pre-wrap break-words">{{ formatCell(row?.[column]) }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p class="mt-2 text-[11px] tabular-nums" style="color: var(--color-text-muted);">
      {{ rowSummary }}
    </p>
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
