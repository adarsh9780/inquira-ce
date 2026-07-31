<template>
  <section class="flex flex-col overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] shadow-sm" :aria-labelledby="`table-${table.id}-title`">
    <div class="sticky top-0 z-30 flex items-center justify-between border-b border-[var(--color-border)] bg-[var(--color-surface)]/95 px-4 py-3 backdrop-blur-sm">
      <div class="min-w-0">
        <h3 :id="`table-${table.id}-title`" class="flex items-center gap-2 truncate font-mono text-[14px] font-semibold text-[var(--color-text-main)]">
          <svg class="h-4 w-4 shrink-0 text-[var(--color-accent)]" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"></path></svg>
          {{ table.tableName }}
        </h3>
        <p class="mt-1 text-[11px] text-[var(--color-text-muted)]">{{ table.columns.length }} columns<span v-if="table.rowCount"> · {{ table.rowCount.toLocaleString() }} rows</span><span v-if="table.status"> · {{ table.status }}</span></p>
      </div>
      <div class="flex items-center gap-2">
        <button type="button" :disabled="busy" class="flex items-center gap-1 rounded px-2 py-1 text-[12px] font-medium text-[var(--color-accent)] transition-colors hover:bg-[var(--color-accent)]/10 disabled:cursor-not-allowed disabled:opacity-50" @click="$emit('regenerate', table.tableName)">
          <span v-if="regenerating" class="inquira-spinner h-3.5 w-3.5 border-2"></span>
          {{ regenerating ? 'Regenerating…' : 'Regenerate' }}
        </button>
        <button type="button" :disabled="(!dirty && !draftChanged) || busy" class="rounded-md bg-[var(--color-accent)] px-3 py-1.5 text-[12px] font-semibold text-[var(--color-on-accent)] shadow-sm transition-all hover:brightness-95 disabled:opacity-50" @click="saveTable">{{ saving ? 'Saving…' : 'Save table' }}</button>
      </div>
    </div>

    <div class="overflow-x-auto">
      <table class="w-full min-w-[840px] border-collapse text-left">
        <thead class="sticky top-[61px] z-20 border-b border-[var(--color-border)] bg-[var(--color-surface)]">
          <tr>
            <th class="w-12 border-b border-[var(--color-border)] px-4 py-2.5 text-center text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]">#</th>
            <th class="w-1/5 border-b border-[var(--color-border)] px-4 py-2.5 text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]">Column</th>
            <th class="w-28 border-b border-[var(--color-border)] px-3 py-2.5 text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]">Type</th>
            <th class="w-20 border-b border-[var(--color-border)] px-3 py-2.5 text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]">Nullable</th>
            <th class="w-[30%] border-b border-[var(--color-border)] px-4 py-2.5 text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]">Description</th>
            <th class="w-[25%] border-b border-[var(--color-border)] px-4 py-2.5 text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]">Aliases</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-[var(--color-border)]">
          <tr v-for="(column, index) in table.columns" :key="column.name" class="align-top transition-colors hover:bg-[var(--color-base-muted)]">
            <td class="w-12 px-4 py-3.5 text-center text-[12px] text-[var(--color-text-sub)]">{{ index + 1 }}</td>
            <td class="px-4 py-3.5 font-mono text-[13px] font-semibold text-[var(--color-text-main)]">{{ column.name }}</td>
            <td class="px-3 py-3.5 font-mono text-[12px] text-[var(--color-text-sub)]">{{ column.dataType }}</td>
            <td class="px-3 py-3.5 text-[12px] text-[var(--color-text-sub)]">{{ column.nullable ? 'Yes' : 'No' }}</td>
            <td class="relative cursor-pointer px-4 py-2" @click="startEdit(column, 'description')">
              <textarea v-if="isEditing(column, 'description')" v-focus v-model="editValue" :aria-label="`Description for ${column.name}`" class="min-h-[60px] w-full resize-y rounded-md border border-[var(--color-accent)] bg-[var(--color-base)] p-2 text-[13px] text-[var(--color-text-main)] shadow-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/20" @click.stop @blur="commitEdit" @keydown.esc.prevent="cancelEdit" @keydown.ctrl.enter.prevent="commitEdit"></textarea>
              <span v-else-if="column.description" class="block min-h-[28px] py-1.5 pr-4 text-[13px] whitespace-pre-wrap text-[var(--color-text-main)]">{{ column.description }}</span>
              <span v-else class="block min-h-[28px] py-1.5 text-[12px] italic text-[var(--color-text-muted)]">Click to add description...</span>
            </td>
            <td class="relative cursor-pointer px-4 py-2" @click="startEdit(column, 'aliases')">
              <input v-if="isEditing(column, 'aliases')" v-focus v-model="editValue" :aria-label="`Aliases for ${column.name}`" class="w-full rounded-md border border-[var(--color-accent)] bg-[var(--color-base)] p-2 text-[13px] text-[var(--color-text-main)] shadow-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/20" @click.stop @blur="commitEdit" @keydown.esc.prevent="cancelEdit" @keydown.enter.prevent="commitEdit" />
              <div v-else-if="column.aliases.length" class="flex min-h-[28px] flex-wrap gap-1.5 py-1.5"><span v-for="alias in column.aliases" :key="alias" class="rounded border border-[var(--color-border)] bg-[var(--color-base-muted)] px-2 py-0.5 font-mono text-[11px] text-[var(--color-text-main)] shadow-sm">{{ alias }}</span></div>
              <span v-else class="block min-h-[28px] py-1.5 text-[12px] italic text-[var(--color-text-muted)]">Click to add aliases...</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { normalizeAliasList } from '../../composables/useSchemaHubState'
import type { SchemaHubColumn, SchemaHubTable } from '../../types/schemaHub'

const props = defineProps<{ table: SchemaHubTable; dirty: boolean; saving: boolean; regenerating: boolean; busy: boolean }>()
const emit = defineEmits<{ change: [tableId: string, columns: SchemaHubColumn[]]; save: [tableId: string, columns: SchemaHubColumn[]]; regenerate: [tableName: string] }>()
const vFocus = { mounted: (element: HTMLElement) => element.focus() }
const editing = ref<{ columnName: string; field: 'description' | 'aliases'; value: string } | null>(null)
const editValue = computed({ get: () => editing.value?.value || '', set: (value: string) => { if (editing.value) editing.value.value = value } })

const draftChanged = computed(() => editing.value ? columnsWithEdit() !== props.table.columns : false)
function isEditing(column: SchemaHubColumn, field: 'description' | 'aliases') { return editing.value?.columnName === column.name && editing.value.field === field }
function startEdit(column: SchemaHubColumn, field: 'description' | 'aliases') {
  if (editing.value) commitEdit()
  editing.value = { columnName: column.name, field, value: field === 'description' ? column.description : column.aliases.join(', ') }
}
function columnsWithEdit() {
  if (!editing.value) return props.table.columns
  const active = editing.value
  const column = props.table.columns.find((item) => item.name === active.columnName)
  if (!column) return props.table.columns
  const value = active.field === 'description' ? active.value : normalizeAliasList(active.value)
  const unchanged = active.field === 'description' ? column.description === value : JSON.stringify(column.aliases) === JSON.stringify(value)
  return unchanged ? props.table.columns : props.table.columns.map((item) => item.name === column.name ? { ...item, [active.field]: value } : item)
}
function commitEdit() {
  const columns = columnsWithEdit()
  editing.value = null
  if (columns !== props.table.columns) emit('change', props.table.id, columns)
}
function cancelEdit() { editing.value = null }
function saveTable() {
  const columns = columnsWithEdit()
  editing.value = null
  emit('save', props.table.id, columns)
}
</script>
