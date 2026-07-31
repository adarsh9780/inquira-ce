<template>
  <div class="inquira-data-grid" data-inquira-data-grid>
    <DataGridViewport fill label="Scrollable table data" class="inquira-data-grid__viewport">
      <table
        class="inquira-data-grid__table"
        :style="{ width: `max(100%, ${table.getTotalSize()}px)` }"
        role="grid"
        aria-label="Table data"
        :aria-rowcount="displayRowCount"
        :aria-colcount="props.columns.length"
      >
        <thead>
          <tr v-for="headerGroup in table.getHeaderGroups()" :key="headerGroup.id">
            <th
              v-for="header in headerGroup.headers"
              :key="header.id"
              :style="columnSizeStyle(header.getSize())"
              scope="col"
              :aria-sort="columnAriaSort(header.column)"
            >
              <div class="inquira-data-grid__header-content">
                <button
                  type="button"
                  class="inquira-data-grid__sort-button"
                  :class="header.column.getIsSorted() ? 'is-active' : ''"
                  :aria-label="sortButtonLabel(header.column)"
                  @click="header.column.getToggleSortingHandler()?.($event)"
                >
                  <span class="inquira-data-grid__header-label">
                    <FlexRender
                      v-if="!header.isPlaceholder"
                      :render="header.column.columnDef.header"
                      :props="header.getContext()"
                    />
                  </span>
                  <ChevronUpIcon
                    v-if="header.column.getIsSorted() === 'asc'"
                    class="h-3.5 w-3.5 shrink-0"
                    aria-hidden="true"
                  />
                  <ChevronDownIcon
                    v-else-if="header.column.getIsSorted() === 'desc'"
                    class="h-3.5 w-3.5 shrink-0"
                    aria-hidden="true"
                  />
                  <ChevronUpDownIcon
                    v-else
                    class="inquira-data-grid__sort-idle h-3.5 w-3.5 shrink-0"
                    aria-hidden="true"
                  />
                </button>

                <button
                  type="button"
                  class="inquira-data-grid__filter-button"
                  :class="hasColumnFilter(header.column.id) ? 'is-active' : ''"
                  :aria-label="`Filter ${header.column.id}`"
                  :aria-pressed="hasColumnFilter(header.column.id)"
                  @click.stop="openFilterMenu($event, header.column.id)"
                >
                  <FunnelIcon class="h-3.5 w-3.5" aria-hidden="true" />
                </button>
              </div>

              <div
                v-if="header.column.getCanResize()"
                class="inquira-data-grid__resize-handle"
                :class="header.column.getIsResizing() ? 'is-resizing' : ''"
                role="separator"
                aria-orientation="vertical"
                :aria-label="`Resize ${header.column.id} column`"
                @dblclick="header.column.resetSize()"
                @mousedown="header.getResizeHandler()?.($event)"
                @touchstart="header.getResizeHandler()?.($event)"
              ></div>
            </th>
          </tr>
        </thead>

        <tbody>
          <tr
            v-for="(row, visibleRowIndex) in visibleRows"
            :key="row.id"
            :aria-rowindex="query.pageIndex * query.pageSize + visibleRowIndex + 2"
          >
            <td
              v-for="cell in row.getVisibleCells()"
              :key="cell.id"
              :style="columnSizeStyle(cell.column.getSize())"
              tabindex="0"
              :title="cellTitle(cell.getValue())"
              @keydown="copyCellOnShortcut($event, cell.getValue())"
            >
              <span v-if="cell.getValue() == null" class="inquira-data-grid__null">null</span>
              <span v-else class="inquira-data-grid__cell-value">{{ formatCellValue(cell.getValue()) }}</span>
            </td>
          </tr>

          <tr v-if="visibleRows.length === 0">
            <td :colspan="Math.max(1, props.columns.length)" class="inquira-data-grid__no-results">
              No matching rows
            </td>
          </tr>
        </tbody>
      </table>
    </DataGridViewport>

    <div class="inquira-data-grid__pagination" aria-label="Table pagination">
      <span class="inquira-data-grid__range">{{ visibleRangeLabel }}</span>
      <div class="inquira-data-grid__page-controls">
        <button
          type="button"
          class="inquira-data-grid__page-button"
          :disabled="!table.getCanPreviousPage() || loading"
          aria-label="First page"
          title="First page"
          @click="table.setPageIndex(0)"
        >
          <ChevronDoubleLeftIcon class="h-4 w-4" aria-hidden="true" />
        </button>
        <button
          type="button"
          class="inquira-data-grid__page-button"
          :disabled="!table.getCanPreviousPage() || loading"
          aria-label="Previous page"
          title="Previous page"
          @click="table.previousPage()"
        >
          <ChevronLeftIcon class="h-4 w-4" aria-hidden="true" />
        </button>
        <span class="inquira-data-grid__page-label">
          Page {{ currentPageNumber }} of {{ pageCount }}
        </span>
        <button
          type="button"
          class="inquira-data-grid__page-button"
          :disabled="!table.getCanNextPage() || loading"
          aria-label="Next page"
          title="Next page"
          @click="table.nextPage()"
        >
          <ChevronRightIcon class="h-4 w-4" aria-hidden="true" />
        </button>
        <button
          type="button"
          class="inquira-data-grid__page-button"
          :disabled="!table.getCanNextPage() || loading"
          aria-label="Last page"
          title="Last page"
          @click="table.setPageIndex(Math.max(0, pageCount - 1))"
        >
          <ChevronDoubleRightIcon class="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
    </div>
  </div>

  <Teleport to="body">
    <Transition name="motion-popover">
    <form
      v-if="filterMenu.columnId"
      ref="filterMenuElement"
      class="inquira-table-filter-menu motion-popover-surface"
      :style="{ left: `${filterMenu.x}px`, top: `${filterMenu.y}px` }"
      role="dialog"
      :aria-label="`Filter ${filterMenu.columnId}`"
      @submit.prevent="applyColumnFilter"
    >
      <div class="inquira-table-filter-menu__heading">
        <span class="truncate">Filter {{ filterMenu.columnId }}</span>
        <button
          type="button"
          class="inquira-table-filter-menu__close"
          aria-label="Close filter"
          @click="closeFilterMenu"
        >
          <XMarkIcon class="h-4 w-4" aria-hidden="true" />
        </button>
      </div>

      <label class="inquira-table-filter-menu__field">
        <span>Condition</span>
        <select v-model="filterDraft.operator" class="inquira-table-filter-menu__control">
          <option v-for="option in activeFilterOperators" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
      </label>

      <label
        v-if="!isValuelessFilterOperator(filterDraft.operator) && filterDraft.kind === 'boolean'"
        class="inquira-table-filter-menu__field"
      >
        <span>Value</span>
        <select v-model="filterDraft.value" class="inquira-table-filter-menu__control">
          <option :value="true">True</option>
          <option :value="false">False</option>
        </select>
      </label>

      <label
        v-else-if="!isValuelessFilterOperator(filterDraft.operator)"
        class="inquira-table-filter-menu__field"
      >
        <span>Value</span>
        <input
          v-model="filterDraft.value"
          :type="filterDraft.kind === 'number' ? 'number' : 'text'"
          class="inquira-table-filter-menu__control"
          autocomplete="off"
          autofocus
        />
      </label>

      <label
        v-if="filterDraft.operator === 'inRange'"
        class="inquira-table-filter-menu__field"
      >
        <span>And</span>
        <input
          v-model="filterDraft.valueTo"
          type="number"
          class="inquira-table-filter-menu__control"
          autocomplete="off"
        />
      </label>

      <div class="inquira-table-filter-menu__actions">
        <button
          type="button"
          class="inquira-table-filter-menu__clear"
          :disabled="!hasColumnFilter(filterMenu.columnId)"
          @click="clearColumnFilter"
        >
          Clear
        </button>
        <button
          type="submit"
          class="inquira-table-filter-menu__apply"
          :disabled="!isCompleteTableFilter(filterDraft)"
        >
          Apply
        </button>
      </div>
    </form>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import {
  FlexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useVueTable,
} from '@tanstack/vue-table'
import {
  ChevronDoubleLeftIcon,
  ChevronDoubleRightIcon,
  ChevronDownIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ChevronUpDownIcon,
  ChevronUpIcon,
  FunnelIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'
import DataGridViewport from '../../ui/DataGridViewport.vue'
import {
  fromTanStackSorting,
  getFilterOperators,
  inferTableFilterKind,
  isCompleteTableFilter,
  isValuelessFilterOperator,
  resolveTableStateUpdater,
  tableColumnFilter,
  tableGlobalFilter,
  toTanStackColumnFilters,
  toTanStackSorting,
} from './tableQuery'

const props = defineProps({
  rows: { type: Array, default: () => [] },
  columns: { type: Array, default: () => [] },
  rowCount: { type: Number, default: 0 },
  query: { type: Object, required: true },
  manual: { type: Boolean, default: false },
  globalFilter: { type: String, default: '' },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:query'])
const filterMenuElement = ref<any>(null)
const filterMenu = reactive<any>({ columnId: '', x: 0, y: 0 })
const filterDraft = reactive<any>({ kind: 'text', operator: 'contains', value: '', valueTo: '' })

const tableColumns = computed(() => props.columns.map((name) => ({
  id: String(name),
  accessorFn: (row: any) => row?.[String(name)],
  header: String(name),
  minSize: 120,
  size: 160,
  maxSize: 800,
  sortDescFirst: false,
  filterFn: tableColumnFilter,
})))

const tanStackSorting = computed(() => toTanStackSorting(props.query?.sorting))
const tanStackColumnFilters = computed(() => toTanStackColumnFilters(props.query?.filters))
const pagination = computed(() => ({
  pageIndex: Math.max(0, Number(props.query?.pageIndex || 0)),
  pageSize: Math.max(1, Number(props.query?.pageSize || 100)),
}))
const manualPageCount = computed(() => Math.max(1, Math.ceil(Math.max(0, props.rowCount) / pagination.value.pageSize)))

const table = useVueTable({
  get data() { return props.rows },
  get columns() { return tableColumns.value },
  state: {
    get sorting() { return tanStackSorting.value },
    get columnFilters() { return tanStackColumnFilters.value },
    get globalFilter() { return props.globalFilter },
    get pagination() { return pagination.value },
  },
  get manualPagination() { return props.manual },
  get manualSorting() { return props.manual },
  get manualFiltering() { return props.manual },
  get pageCount() { return props.manual ? manualPageCount.value : undefined },
  enableMultiSort: true,
  columnResizeMode: 'onChange',
  defaultColumn: { minSize: 120, size: 160, maxSize: 800 },
  globalFilterFn: tableGlobalFilter,
  getCoreRowModel: getCoreRowModel(),
  getFilteredRowModel: getFilteredRowModel(),
  getSortedRowModel: getSortedRowModel(),
  getPaginationRowModel: getPaginationRowModel(),
  onSortingChange: (updater) => {
    const nextSorting = resolveTableStateUpdater(updater, tanStackSorting.value)
    emitQuery({
      pageIndex: 0,
      sorting: fromTanStackSorting(nextSorting),
    })
  },
  onPaginationChange: (updater) => {
    const nextPagination = resolveTableStateUpdater(updater, pagination.value)
    emitQuery({ pageIndex: Math.max(0, Number(nextPagination?.pageIndex || 0)) })
  },
})

const visibleRows = computed(() => table.getRowModel().rows)
const displayRowCount = computed(() => {
  if (props.manual) return Math.max(0, Number(props.rowCount || 0))
  return table.getFilteredRowModel().rows.length
})
const pageCount = computed(() => Math.max(1, table.getPageCount()))
const currentPageNumber = computed(() => Math.min(pageCount.value, pagination.value.pageIndex + 1))
const visibleRangeLabel = computed(() => {
  const total = displayRowCount.value
  if (total <= 0 || visibleRows.value.length === 0) return `0 of ${total.toLocaleString()}`
  const start = pagination.value.pageIndex * pagination.value.pageSize + 1
  const end = Math.min(total, start + visibleRows.value.length - 1)
  return `${start.toLocaleString()}–${end.toLocaleString()} of ${total.toLocaleString()}`
})
const activeFilterOperators = computed(() => getFilterOperators(filterDraft.kind))

watch(() => props.columns, () => closeFilterMenu())

onMounted(() => {
  document.addEventListener('pointerdown', onDocumentPointerDown)
  document.addEventListener('keydown', onDocumentKeyDown)
  window.addEventListener('resize', closeFilterMenu)
})

onUnmounted(() => {
  document.removeEventListener('pointerdown', onDocumentPointerDown)
  document.removeEventListener('keydown', onDocumentKeyDown)
  window.removeEventListener('resize', closeFilterMenu)
})

function emitQuery(patch: any) {
  emit('update:query', {
    pageIndex: pagination.value.pageIndex,
    pageSize: pagination.value.pageSize,
    sorting: Array.isArray(props.query?.sorting) ? props.query.sorting : [],
    filters: Array.isArray(props.query?.filters) ? props.query.filters : [],
    ...patch,
  })
}

function columnSizeStyle(size: any) {
  return { width: `${size}px`, minWidth: `${size}px`, maxWidth: `${size}px` }
}

function columnAriaSort(column: any) {
  const sort = column.getIsSorted()
  if (sort === 'asc') return 'ascending'
  if (sort === 'desc') return 'descending'
  return 'none'
}

function sortButtonLabel(column: any) {
  const sort = column.getIsSorted()
  if (sort === 'asc') return `Sort ${column.id} descending`
  if (sort === 'desc') return `Clear sorting for ${column.id}`
  return `Sort ${column.id} ascending`
}

function hasColumnFilter(columnId: any) {
  return (props.query?.filters || []).some((entry: any) => entry?.columnId === columnId)
}

function openFilterMenu(event: any, columnId: any) {
  if (filterMenu.columnId === columnId) {
    closeFilterMenu()
    return
  }
  const existing = (props.query?.filters || []).find((entry: any) => entry?.columnId === columnId)
  const kind = existing?.kind || inferTableFilterKind(props.rows, columnId)
  const rect = event.currentTarget.getBoundingClientRect()
  const menuWidth = 248
  filterMenu.columnId = columnId
  filterMenu.x = Math.max(8, Math.min(rect.right - menuWidth, window.innerWidth - menuWidth - 8))
  filterMenu.y = Math.max(8, Math.min(rect.bottom + 6, window.innerHeight - 280))
  filterDraft.kind = kind
  filterDraft.operator = existing?.operator || (kind === 'text' ? 'contains' : 'equals')
  filterDraft.value = existing?.value ?? (kind === 'boolean' ? true : '')
  filterDraft.valueTo = existing?.valueTo ?? ''
}

function closeFilterMenu() {
  filterMenu.columnId = ''
}

function applyColumnFilter() {
  if (!filterMenu.columnId || !isCompleteTableFilter(filterDraft)) return
  const nextFilter = {
    columnId: filterMenu.columnId,
    kind: filterDraft.kind,
    operator: filterDraft.operator,
    value: filterDraft.value,
    valueTo: filterDraft.valueTo,
  }
  const filters = (props.query?.filters || []).filter((entry: any) => entry?.columnId !== filterMenu.columnId)
  filters.push(nextFilter)
  emitQuery({ pageIndex: 0, filters })
  closeFilterMenu()
}

function clearColumnFilter() {
  if (!filterMenu.columnId) return
  const filters = (props.query?.filters || []).filter((entry: any) => entry?.columnId !== filterMenu.columnId)
  emitQuery({ pageIndex: 0, filters })
  closeFilterMenu()
}

function onDocumentPointerDown(event: any) {
  if (!filterMenu.columnId || filterMenuElement.value?.contains(event.target)) return
  closeFilterMenu()
}

function onDocumentKeyDown(event: any) {
  if (event.key === 'Escape') closeFilterMenu()
}

function formatCellValue(value: any) {
  const formatted = typeof value === 'number' ? value.toLocaleString() : String(value)
  return formatted.length > 120 ? `${formatted.slice(0, 120)}…` : formatted
}

function cellTitle(value: any) {
  if (value == null) return 'null'
  return typeof value === 'number' ? value.toLocaleString() : String(value)
}

async function copyCellOnShortcut(event: any, value: any) {
  if (!(event.key.toLowerCase() === 'c' && (event.metaKey || event.ctrlKey))) return
  event.preventDefault()
  const text = value == null ? '' : String(value)
  try {
    await navigator.clipboard?.writeText(text)
  } catch (_) {
    // Browser text selection remains available when clipboard access is denied.
  }
}
</script>

<style scoped>
.inquira-data-grid {
  position: absolute;
  inset: 0;
  display: flex;
  min-width: 0;
  flex-direction: column;
  overflow: hidden;
  background: var(--color-base);
  color: var(--color-text-main);
  font-family: var(--font-ui);
}

.inquira-data-grid__table {
  table-layout: fixed;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 13px;
  line-height: 1.4;
}

.inquira-data-grid thead {
  position: sticky;
  top: 0;
  z-index: 3;
}

.inquira-data-grid th {
  position: relative;
  height: 34px;
  padding: 0;
  border-right: 1px solid var(--color-border);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-data-grid-header);
  color: var(--color-text-main);
  font-size: 12px;
  font-weight: 650;
  text-align: left;
}

.inquira-data-grid td {
  height: 30px;
  overflow: hidden;
  padding: 0 8px;
  border-right: 1px solid var(--color-border);
  border-bottom: 1px solid color-mix(in srgb, var(--color-border) 72%, transparent);
  color: var(--color-text-main);
  font-size: 13px;
  font-weight: 400;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.inquira-data-grid th:last-child,
.inquira-data-grid td:last-child {
  border-right: 0;
}

.inquira-data-grid tbody tr:nth-child(even) td {
  background: var(--color-data-grid-row-alt);
}

.inquira-data-grid tbody tr:hover td {
  background: var(--color-data-grid-row-hover);
}

.inquira-data-grid td:focus-visible {
  position: relative;
  z-index: 1;
  outline: 2px solid var(--color-accent);
  outline-offset: -2px;
}

.inquira-data-grid__header-content {
  display: flex;
  height: 100%;
  min-width: 0;
  align-items: center;
  padding: 0 5px 0 8px;
}

.inquira-data-grid__sort-button {
  display: flex;
  min-width: 0;
  flex: 1;
  align-items: center;
  gap: 5px;
  color: inherit;
  text-align: left;
}

.inquira-data-grid__sort-button:focus-visible,
.inquira-data-grid__filter-button:focus-visible,
.inquira-data-grid__page-button:focus-visible,
.inquira-table-filter-menu button:focus-visible,
.inquira-table-filter-menu__control:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 1px;
}

.inquira-data-grid__header-label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.inquira-data-grid__sort-button.is-active,
.inquira-data-grid__filter-button.is-active {
  color: var(--color-accent);
}

.inquira-data-grid__sort-idle {
  color: var(--color-text-sub);
  opacity: 0;
  transition: opacity 120ms ease;
}

.inquira-data-grid th:hover .inquira-data-grid__sort-idle,
.inquira-data-grid__sort-button:focus-visible .inquira-data-grid__sort-idle {
  opacity: 0.72;
}

.inquira-data-grid__filter-button {
  display: inline-flex;
  height: 24px;
  width: 24px;
  flex: none;
  align-items: center;
  justify-content: center;
  border-radius: 5px;
  color: var(--color-text-sub);
  opacity: 0.62;
}

.inquira-data-grid__filter-button:hover,
.inquira-data-grid__filter-button:focus-visible,
.inquira-data-grid__filter-button.is-active {
  background: var(--color-base-muted);
  opacity: 1;
}

.inquira-data-grid__resize-handle {
  position: absolute;
  z-index: 4;
  top: 0;
  right: -3px;
  width: 6px;
  height: 100%;
  cursor: col-resize;
  touch-action: none;
  user-select: none;
}

.inquira-data-grid__resize-handle::after {
  position: absolute;
  top: 0;
  right: 2px;
  width: 1px;
  height: 100%;
  background: var(--color-border);
  content: '';
}

.inquira-data-grid__resize-handle:hover::after,
.inquira-data-grid__resize-handle.is-resizing::after {
  width: 2px;
  background: var(--color-accent);
}

.inquira-data-grid__null {
  color: var(--color-text-muted);
  font-style: italic;
}

.inquira-data-grid__cell-value {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
}

.inquira-data-grid__no-results {
  height: 72px !important;
  color: var(--color-text-muted) !important;
  text-align: center;
}

.inquira-data-grid__pagination {
  display: flex;
  min-height: 36px;
  flex: none;
  align-items: center;
  justify-content: flex-end;
  gap: 16px;
  border-top: 1px solid var(--color-border);
  background: var(--color-data-grid-footer);
  padding: 0 8px 0 12px;
  color: var(--color-text-muted);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.inquira-data-grid__range {
  white-space: nowrap;
}

.inquira-data-grid__page-controls {
  display: flex;
  align-items: center;
  gap: 2px;
}

.inquira-data-grid__page-button {
  display: inline-flex;
  height: 26px;
  width: 26px;
  align-items: center;
  justify-content: center;
  border-radius: 5px;
  color: var(--color-text-muted);
}

.inquira-data-grid__page-button:hover:not(:disabled) {
  background: var(--color-base-muted);
  color: var(--color-text-main);
}

.inquira-data-grid__page-button:disabled {
  cursor: not-allowed;
  opacity: 0.35;
}

.inquira-data-grid__page-label {
  min-width: 92px;
  padding: 0 4px;
  color: var(--color-text-main);
  text-align: center;
  white-space: nowrap;
}

.inquira-table-filter-menu {
  position: fixed;
  z-index: 10020;
  display: flex;
  width: 248px;
  flex-direction: column;
  gap: 10px;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  background: var(--color-panel-elevated, var(--color-surface));
  box-shadow: var(--shadow-lifted);
  padding: 10px;
  color: var(--color-text-main);
  font-family: var(--font-ui);
  font-size: 12px;
}

.inquira-table-filter-menu__heading {
  display: flex;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-weight: 650;
}

.inquira-table-filter-menu__close {
  display: inline-flex;
  height: 24px;
  width: 24px;
  flex: none;
  align-items: center;
  justify-content: center;
  border-radius: 5px;
  color: var(--color-text-muted);
}

.inquira-table-filter-menu__close:hover {
  background: var(--color-base-muted);
  color: var(--color-text-main);
}

.inquira-table-filter-menu__field {
  display: flex;
  flex-direction: column;
  gap: 5px;
  color: var(--color-text-muted);
  font-weight: 500;
}

.inquira-table-filter-menu__control {
  width: 100%;
  height: 32px;
  border: 1px solid var(--color-border);
  border-radius: 7px;
  background: var(--color-base);
  padding: 0 8px;
  color: var(--color-text-main);
  font-size: 12px;
  font-weight: 400;
}

.inquira-table-filter-menu__actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding-top: 2px;
}

.inquira-table-filter-menu__clear,
.inquira-table-filter-menu__apply {
  height: 30px;
  border-radius: 7px;
  padding: 0 10px;
  font-weight: 600;
}

.inquira-table-filter-menu__clear {
  color: var(--color-text-muted);
}

.inquira-table-filter-menu__clear:hover:not(:disabled) {
  background: var(--color-base-muted);
  color: var(--color-text-main);
}

.inquira-table-filter-menu__clear:disabled {
  opacity: 0.4;
}

.inquira-table-filter-menu__apply {
  background: var(--color-accent);
  color: var(--color-accent-contrast, white);
}

.inquira-table-filter-menu__apply:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

@media (max-width: 640px) {
  .inquira-data-grid__pagination {
    justify-content: space-between;
    gap: 6px;
  }

  .inquira-data-grid__page-controls {
    gap: 0;
  }

  .inquira-data-grid__page-label {
    min-width: 76px;
    font-size: 11px;
  }
}
</style>
