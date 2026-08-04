import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('table toolbar keeps a contextual artifact selector with search and icon actions', () => {
  const tableTabPath = resolve(process.cwd(), 'src/components/analysis/TableTab.vue')
  const tableToolbarPath = resolve(process.cwd(), 'src/components/analysis/table/TableToolbar.vue')
  const source = readFileSync(tableTabPath, 'utf-8')
  const toolbar = readFileSync(tableToolbarPath, 'utf-8')

  assert.equal(source.includes('Teleport to="#workspace-right-pane-toolbar-right"'), true)
  assert.equal(source.includes('Teleport to="#workspace-right-pane-toolbar-center"'), true)
  assert.equal(source.includes('aria-label="Select table"'), true)
  assert.equal(source.includes('<TableToolbar'), true)
  assert.equal(toolbar.includes('class="flex min-w-0 items-center justify-end w-full gap-2"'), true)
  assert.equal(source.includes('FunnelIcon'), true)
  assert.equal(source.includes("toolbarMode === 'wide' ? 'w-[19rem]'"), true)
  assert.equal(source.includes("v-if=\"toolbarMode === 'wide'\" class=\"relative w-[13.5rem]"), true)
  assert.equal(source.includes("v-if=\"toolbarMode === 'compact'\""), true)
  assert.equal(source.includes("toolbarMode === 'minimal'"), true)
  assert.equal(source.includes("{ id: 'search', label: tableSearch.value ? 'Edit row search' : 'Search rows' }"), true)
  assert.equal(source.includes("{ id: 'export', label: 'Export CSV'"), true)
  assert.equal(source.includes('class="input-base h-8 pl-8 pr-2"'), true)
  assert.equal(source.includes('style="background-color: var(--color-surface); border-color: var(--color-border);"'), true)
  assert.equal(source.includes('title="Table actions"'), true)
  assert.equal(source.includes("label: 'Delete table'"), true)
  assert.equal(source.includes(`:title="isDownloading ? 'Exporting CSV' : 'Export CSV'"`), true)
  assert.equal(source.includes('class="btn-icon h-8 w-8 shrink-0 border"'), true)
  assert.equal(source.includes('style="border-color: var(--color-border); color: var(--color-text-muted);"'), true)
})

test('table csv export uses save dialog flow instead of forcing downloads folder', () => {
  const tableTabPath = resolve(process.cwd(), 'src/components/analysis/TableTab.vue')
  const exportUtilPath = resolve(process.cwd(), 'src/utils/exportFile.ts')

  const tableTab = readFileSync(tableTabPath, 'utf-8')
  const exportUtil = readFileSync(exportUtilPath, 'utf-8')

  assert.equal(tableTab.includes("import { persistExportFile } from '../../utils/exportFile'"), true)
  assert.equal(tableTab.includes('const exported = await persistExportFile({'), true)
  assert.equal(tableTab.includes("toast.info('Export canceled')"), true)
  assert.equal(tableTab.includes("toast.success('Export complete'"), true)
  assert.equal(exportUtil.includes('showSaveFilePicker'), true)
})
