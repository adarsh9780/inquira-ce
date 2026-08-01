<template>
  <section class="flex min-h-0 flex-1 flex-col overflow-hidden bg-[var(--color-base)]" :aria-label="`Preview of ${table.tableName}`">
    <header class="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-2.5">
      <p class="text-[11px] text-[var(--color-text-muted)]">
        {{ previewSummary }} · session-cached snapshot
      </p>
      <SegmentedControl
        v-model="edge"
        :options="edgeOptions"
        aria-label="Dataset preview rows"
      />
    </header>

    <div class="relative min-h-0 flex-1 bg-[var(--color-base)]">
      <div v-if="isLoading && !preview" class="absolute inset-0 flex flex-col items-center justify-center gap-3 text-[13px] text-[var(--color-text-muted)]" role="status">
        <span class="inquira-spinner h-5 w-5 border-2" aria-hidden="true"></span>
        Loading {{ edge === 'head' ? 'first' : 'last' }} rows…
      </div>
      <div v-else-if="error" class="absolute inset-0 flex flex-col items-center justify-center gap-3 px-6 text-center">
        <p class="text-[13px] font-medium text-[var(--color-text-main)]">Preview could not be loaded</p>
        <p class="max-w-md text-[12px] leading-5 text-[var(--color-text-muted)]">{{ error }}</p>
        <button type="button" class="btn-secondary px-3 py-1.5 text-[12px]" @click="retry">Try again</button>
      </div>
      <DataTable
        v-else-if="preview"
        :rows="preview.rows"
        :columns="preview.columns"
        :row-count="preview.rows.length"
        :query="query"
        :loading="isLoading"
        @update:query="updateQuery"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { clearDatasetPreviewCache, useDatasetPreview } from '../../composables/useDatasetPreview'
import type { DatasetPreviewMode } from '../../types/datasetPreview'
import type { SchemaHubTable } from '../../types/schemaHub'
import DataTable from '../analysis/table/DataTable.vue'
import { createTableQuery } from '../analysis/table/tableQuery'
import type { TableQuery } from '../analysis/table/tableQuery'
import SegmentedControl from '../ui/SegmentedControl.vue'

const props = defineProps<{ workspaceId: string; table: SchemaHubTable }>()
const edge = ref<DatasetPreviewMode>('head')
const edgeOptions = [
  { value: 'head', label: 'First 100' },
  { value: 'tail', label: 'Last 100' },
]
const query = ref(createTableQuery())
const { preview, isLoading, error, load } = useDatasetPreview()

const previewSummary = computed(() => {
  if (!preview.value || preview.value.rowCount === 0) return `${props.table.rowCount.toLocaleString()} total rows`
  const start = preview.value.offset + 1
  const end = preview.value.offset + preview.value.rows.length
  return `Rows ${start.toLocaleString()}–${end.toLocaleString()} of ${preview.value.rowCount.toLocaleString()}`
})

watch(
  () => [props.workspaceId, props.table.tableName, edge.value] as const,
  ([workspaceId, tableName, mode]) => {
    query.value = createTableQuery()
    void load(workspaceId, tableName, mode)
  },
  { immediate: true },
)

function retry() {
  clearDatasetPreviewCache(props.workspaceId, props.table.tableName)
  void load(props.workspaceId, props.table.tableName, edge.value)
}

function updateQuery(next: TableQuery) {
  if (JSON.stringify(next) !== JSON.stringify(query.value)) query.value = next
}
</script>
