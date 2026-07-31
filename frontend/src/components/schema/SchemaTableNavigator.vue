<template>
  <aside class="flex w-60 shrink-0 flex-col border-r border-[var(--color-border)] bg-[var(--color-base-muted)] p-3" aria-label="Schema navigation">
    <div class="mb-6 space-y-1">
      <p class="mb-2 px-2 text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">Context</p>
      <button
        type="button"
        class="flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm transition-colors"
        :class="selection.kind === 'workspace' ? 'bg-[var(--color-surface)] font-semibold text-[var(--color-text-main)] shadow-sm' : 'text-[var(--color-text-sub)] hover:bg-[var(--color-surface)]/70'"
        :aria-current="selection.kind === 'workspace' ? 'page' : undefined"
        @click="emit('select', { kind: 'workspace' })"
      >
        <span>Workspace context</span>
        <span class="text-xs font-normal text-[var(--color-text-muted)]">All tables</span>
      </button>
      <button
        type="button"
        class="flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm transition-colors"
        :class="selection.kind === 'sources' ? 'bg-[var(--color-surface)] font-semibold text-[var(--color-text-main)] shadow-sm' : 'text-[var(--color-text-sub)] hover:bg-[var(--color-surface)]/70'"
        :aria-current="selection.kind === 'sources' ? 'page' : undefined"
        @click="emit('select', { kind: 'sources' })"
      >
        <span>Data sources</span>
        <span class="text-xs font-normal tabular-nums text-[var(--color-text-muted)]">{{ sourceCount }}</span>
      </button>
    </div>

    <div class="min-h-0 flex-1 overflow-y-auto">
      <div class="mb-2 flex items-center justify-between px-2">
        <p class="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">Tables</p>
        <span class="text-xs tabular-nums text-[var(--color-text-muted)]">{{ tables.length }}</span>
      </div>
      <ul class="space-y-1" aria-label="Workspace tables">
        <li v-for="table in tables" :key="table.id">
          <button
            type="button"
            class="group flex w-full items-start justify-between gap-2 rounded-lg px-3 py-2 text-left transition-colors"
            :class="isSelected(table.id) ? 'bg-[var(--color-surface)] text-[var(--color-text-main)] shadow-sm' : 'text-[var(--color-text-sub)] hover:bg-[var(--color-surface)]/70'"
            :aria-current="isSelected(table.id) ? 'page' : undefined"
            @click="emit('select', { kind: 'table', tableId: table.id })"
          >
            <span class="min-w-0">
              <span class="block truncate font-mono text-sm font-medium">{{ table.tableName }}</span>
              <span class="mt-1 block text-xs text-[var(--color-text-muted)]">{{ table.columns.length }} columns<span v-if="table.rowCount"> · {{ table.rowCount.toLocaleString() }} rows</span></span>
            </span>
            <span v-if="dirtyTableIds.has(table.id)" class="mt-1 h-2 w-2 shrink-0 rounded-full bg-[var(--color-warning)]" title="Unsaved changes" aria-label="Unsaved changes"></span>
          </button>
        </li>
      </ul>
    </div>
  </aside>
</template>

<script setup lang="ts">
import type { SchemaHubSelection, SchemaHubTable } from '../../types/schemaHub'

const props = withDefaults(defineProps<{ tables: SchemaHubTable[]; selection: SchemaHubSelection; dirtyTableIds: Set<string>; sourceCount?: number }>(), { sourceCount: 0 })
const emit = defineEmits<{ select: [selection: SchemaHubSelection] }>()
function isSelected(tableId: string) { return props.selection.kind === 'table' && props.selection.tableId === tableId }
</script>
