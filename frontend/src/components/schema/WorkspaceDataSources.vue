<template>
  <section class="mx-auto w-full max-w-5xl p-4 pb-10" aria-labelledby="workspace-sources-title">
    <div class="flex items-start justify-between gap-4 border-b border-[var(--color-border)] pb-4">
      <div>
        <h3 id="workspace-sources-title" class="text-sm font-semibold text-[var(--color-text-main)]">Data sources</h3>
        <p class="mt-1 text-xs leading-5 text-[var(--color-text-muted)]">Manage refreshable snapshots from CSV, Parquet, Excel, JSON, and SQLite.</p>
      </div>
      <button type="button" class="btn-primary shrink-0 px-3 py-1.5 text-xs" :disabled="state.busy.value" @click="state.chooseFile">
        {{ state.busy.value && !state.pending.value ? 'Inspecting…' : 'Add data' }}
      </button>
    </div>

    <p v-if="state.error.value" class="mt-4 rounded-lg bg-[var(--color-danger-bg)] px-3 py-2 text-xs text-[var(--color-danger-text)]" role="alert">{{ state.error.value }}</p>

    <div v-if="state.pending.value" class="mt-4 border-b border-[var(--color-border)] pb-5">
      <div class="flex items-start justify-between gap-3">
        <div class="min-w-0">
          <p class="truncate text-xs font-semibold text-[var(--color-text-main)]">{{ state.pending.value.sourcePath }}</p>
          <p class="mt-1 text-[11px] text-[var(--color-text-muted)]">{{ dataSourceKindLabel(state.pending.value.adapterKind) }} · {{ state.pending.value.objects.length }} discovered object{{ state.pending.value.objects.length === 1 ? '' : 's' }}</p>
        </div>
        <button type="button" class="text-xs font-medium text-[var(--color-text-muted)] hover:text-[var(--color-text-main)]" :disabled="state.busy.value" @click="state.cancelPending">Cancel</button>
      </div>

      <label class="mt-4 block">
        <span class="input-label">Source name</span>
        <input v-model="state.pending.value.name" class="input-base input-outlined" maxlength="120" :disabled="state.busy.value" />
      </label>

      <div v-if="isObjectSelectionAdapter(state.pending.value.adapterKind)" class="mt-4 space-y-2">
        <div class="flex items-center justify-between gap-3">
          <span class="input-label">{{ state.pending.value.adapterKind === 'excel' ? 'Sheets' : 'Tables and views' }} · {{ state.pending.value.selectedObjectIds.length }} selected</span>
          <label v-if="state.pending.value.adapterKind === 'excel'" class="flex items-center gap-2 text-xs text-[var(--color-text-muted)]">
            Formula values
            <select v-model="state.pending.value.formulaMode" class="rounded border border-[var(--color-border)] bg-[var(--color-base)] px-2 py-1" :disabled="state.busy.value" @change="state.previewObject(state.pending.value?.activeObjectId)">
              <option value="cached">Last saved values</option>
              <option value="formula">Formula text</option>
            </select>
          </label>
        </div>
        <div v-if="state.pending.value.objects.length > 6" class="flex items-center gap-2">
          <input v-model="state.objectSearch.value" type="search" class="input-base input-outlined h-8 min-w-0 flex-1 text-xs" placeholder="Search source objects" aria-label="Search source objects" />
          <button type="button" class="btn-ghost px-2 py-1 text-xs" :disabled="state.busy.value" @click="state.selectAllObjects">Select all</button>
          <button type="button" class="btn-ghost px-2 py-1 text-xs" :disabled="state.busy.value" @click="state.clearObjectSelection">Clear</button>
        </div>
        <div class="grid max-h-52 gap-2 overflow-y-auto pr-1 sm:grid-cols-2">
          <label v-for="object in state.filteredObjects.value" :key="object.id" class="flex items-start gap-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-base-soft)] p-2">
            <input v-model="state.pending.value.selectedObjectIds" type="checkbox" :value="object.id" :disabled="state.busy.value || object.metadata?.selectable === false" />
            <span class="min-w-0 flex-1">
              <span class="block truncate text-xs font-medium text-[var(--color-text-main)]">{{ object.name }}</span>
              <span class="mt-0.5 block text-[11px] text-[var(--color-text-muted)]">{{ sourceObjectSummary(object, state.pending.value.adapterKind) }}</span>
            </span>
            <button v-if="object.metadata?.selectable !== false" type="button" class="text-[11px] font-medium text-[var(--color-accent)] hover:underline" :disabled="state.busy.value" @click.prevent="state.previewObject(object.id)">Preview</button>
          </label>
        </div>
      </div>

      <DataGridViewport v-if="state.pending.value.previewRows.length" label="Selected source preview" class="mt-4 max-h-48 rounded-md border border-[var(--color-border)]">
        <table class="source-preview-grid">
          <thead><tr><th v-for="column in state.pending.value.columns" :key="column.name">{{ column.name }}</th></tr></thead>
          <tbody><tr v-for="(row, index) in state.pending.value.previewRows.slice(0, 5)" :key="index"><td v-for="column in state.pending.value.columns" :key="column.name" :title="String(row[column.name] ?? '')">{{ row[column.name] ?? '—' }}</td></tr></tbody>
        </table>
      </DataGridViewport>

      <div class="mt-4 flex justify-end">
        <button type="button" class="btn-primary px-4 py-1.5 text-xs" :disabled="state.busy.value || !state.pending.value.name.trim() || !state.pending.value.selectedObjectIds.length" @click="state.create">
          {{ state.busy.value ? 'Adding…' : 'Add source' }}
        </button>
      </div>
    </div>

    <div v-if="state.connections.value.length" class="divide-y divide-[var(--color-border)]">
      <article v-for="item in state.connections.value" :key="item.id" class="flex items-start justify-between gap-4 py-4">
        <div class="min-w-0">
          <div class="flex items-center gap-2">
            <p class="truncate text-sm font-medium text-[var(--color-text-main)]">{{ item.name }}</p>
            <span class="rounded-full bg-[var(--color-success-bg)] px-2 py-0.5 text-[10px] text-[var(--color-success)]">{{ item.status }}</span>
          </div>
          <p class="mt-1 truncate text-xs text-[var(--color-text-muted)]">{{ item.source_path }}</p>
          <p class="mt-1 text-xs tabular-nums text-[var(--color-text-muted)]">{{ dataSourceSummary(item) }}</p>
          <p v-if="item.error_message" class="mt-1 text-xs text-[var(--color-danger-text)]">{{ item.error_message }}</p>
        </div>
        <div class="flex shrink-0 items-center gap-3">
          <button type="button" class="text-xs font-medium text-[var(--color-accent)] hover:underline" :disabled="state.refreshingIds.value.has(String(item.id))" @click="state.refreshConnection(item.id)">{{ state.refreshingIds.value.has(String(item.id)) ? 'Refreshing…' : 'Refresh' }}</button>
          <button type="button" class="text-xs font-medium text-[var(--color-danger)] hover:underline" :disabled="state.busy.value" @click="pendingRemovalId = String(item.id)">Remove</button>
        </div>
      </article>
    </div>
    <div v-else-if="!state.pending.value && !state.busy.value" class="py-16 text-center">
      <p class="text-sm font-medium text-[var(--color-text-main)]">No data sources yet</p>
      <p class="mt-1 text-xs text-[var(--color-text-muted)]">Add a local source to populate this workspace.</p>
    </div>

    <ConfirmationModal :is-open="Boolean(pendingRemovalId)" title="Remove data source?" message="Its local snapshots will be removed from this workspace." confirm-text="Remove" @close="pendingRemovalId = ''" @confirm="confirmRemoval" />
  </section>
</template>

<script setup lang="ts">
import { ref, toRef, watch } from 'vue'
import {
  dataSourceKindLabel,
  dataSourceSummary,
  isObjectSelectionAdapter,
  sourceObjectSummary,
  useWorkspaceDataSources,
} from '../../composables/useWorkspaceDataSources'
import ConfirmationModal from '../modals/ConfirmationModal.vue'
import DataGridViewport from '../ui/DataGridViewport.vue'

const props = defineProps<{ workspaceId: string }>()
const emit = defineEmits<{ changed: []; 'update:count': [count: number] }>()
const pendingRemovalId = ref('')
const state = useWorkspaceDataSources(toRef(props, 'workspaceId'), () => emit('changed'))

watch(state.connections, (items) => emit('update:count', items.length), { immediate: true })

async function confirmRemoval() {
  const id = pendingRemovalId.value
  pendingRemovalId.value = ''
  await state.removeConnection(id)
}

defineExpose({ chooseFile: state.chooseFile, reload: state.load })
</script>

<style scoped>
.source-preview-grid { width: max-content; min-width: 100%; border-collapse: separate; border-spacing: 0; font-size: 0.75rem; text-align: left; }
.source-preview-grid thead { position: sticky; top: 0; z-index: 2; }
.source-preview-grid th, .source-preview-grid td { max-width: 14rem; overflow: hidden; padding: 0.5rem 0.625rem; border-right: 1px solid var(--color-border); border-bottom: 1px solid var(--color-border); text-overflow: ellipsis; white-space: nowrap; }
.source-preview-grid th { background: var(--color-data-grid-header); font-weight: 650; }
</style>
