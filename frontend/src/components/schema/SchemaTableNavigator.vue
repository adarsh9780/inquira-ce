<template>
  <aside class="flex w-64 shrink-0 flex-col border-r border-[var(--color-border)] bg-[var(--color-base-muted)] p-3" aria-label="Dataset browser">
    <div class="mb-3 flex items-center justify-between px-1">
      <h3 class="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">Datasets</h3>
      <span class="text-[11px] tabular-nums text-[var(--color-text-muted)]">{{ tables.length }}</span>
    </div>

    <label class="relative mb-3 block">
      <span class="sr-only">Search datasets</span>
      <svg class="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[var(--color-text-muted)]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></svg>
      <input
        v-model="query"
        type="search"
        class="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-base)] py-1.5 pl-8 pr-2.5 text-[13px] text-[var(--color-text-main)] outline-none placeholder:text-[var(--color-text-muted)] focus:border-[var(--color-accent)] focus:ring-2 focus:ring-[var(--color-accent)]/15"
        placeholder="Search datasets"
      />
    </label>

    <div class="min-h-0 flex-1 overflow-y-auto pr-0.5">
      <ul class="space-y-1" aria-label="Workspace tables">
        <li v-for="table in filteredTables" :key="table.id">
          <button
            type="button"
            class="group flex w-full cursor-pointer items-center gap-2.5 rounded-md border-l-2 px-2.5 py-2 text-left transition-[background-color,color,box-shadow,border-color] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--color-accent)]"
            :class="isSelected(table.id) ? 'border-[var(--color-accent)] bg-[var(--color-surface)] text-[var(--color-text-main)] shadow-sm' : 'border-transparent text-[var(--color-text-sub)] hover:bg-[var(--color-surface)]/70 hover:text-[var(--color-text-main)]'"
            :aria-current="isSelected(table.id) ? 'page' : undefined"
            @click="emit('select', { kind: 'table', tableId: table.id })"
          >
            <span class="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-[var(--color-base)] text-[var(--color-text-muted)] shadow-[inset_0_1px_0_color-mix(in_srgb,var(--color-surface)_80%,transparent)]">
              <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><ellipse cx="12" cy="5" rx="7" ry="3"/><path d="M5 5v7c0 1.7 3.1 3 7 3s7-1.3 7-3V5M5 12v7c0 1.7 3.1 3 7 3s7-1.3 7-3v-7"/></svg>
            </span>
            <span class="min-w-0 flex-1">
              <span class="block truncate font-mono text-[13px] font-medium">{{ table.tableName }}</span>
              <span class="mt-0.5 block truncate text-[11px] text-[var(--color-text-muted)]">{{ table.columns.length }} columns<span v-if="table.rowCount"> · {{ table.rowCount.toLocaleString() }} rows</span></span>
            </span>
            <span v-if="dirtyTableIds.has(table.id)" class="h-2 w-2 shrink-0 rounded-full bg-[var(--color-warning)]" title="Unsaved changes" aria-label="Unsaved changes"></span>
            <svg v-else class="h-3.5 w-3.5 shrink-0 text-[var(--color-text-muted)] opacity-0 transition-opacity group-hover:opacity-100" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="m9 18 6-6-6-6"/></svg>
          </button>
        </li>
      </ul>
      <p v-if="query && filteredTables.length === 0" class="px-2 py-4 text-center text-[12px] leading-5 text-[var(--color-text-muted)]">No datasets match “{{ query }}”.</p>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

import type { SchemaHubSelection, SchemaHubTable } from '../../types/schemaHub'

const props = defineProps<{ tables: SchemaHubTable[]; selection: SchemaHubSelection; dirtyTableIds: Set<string> }>()
const emit = defineEmits<{ select: [selection: SchemaHubSelection] }>()
const query = ref('')
const filteredTables = computed(() => {
  const normalized = query.value.trim().toLocaleLowerCase()
  return normalized ? props.tables.filter((table) => table.tableName.toLocaleLowerCase().includes(normalized)) : props.tables
})
function isSelected(tableId: string) { return props.selection.kind === 'table' && props.selection.tableId === tableId }
</script>
