import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('table toolbar keeps selector flexible and uses icon-only actions with hover labels', () => {
  const tableTabPath = resolve(process.cwd(), 'src/components/analysis/TableTab.vue')
  const source = readFileSync(tableTabPath, 'utf-8')

  assert.equal(source.includes('Teleport to="#workspace-right-pane-toolbar-center"'), true)
  assert.equal(source.includes('Teleport to="#workspace-right-pane-toolbar-right"'), true)
  assert.equal(source.includes('class="flex min-w-0 w-full items-center justify-center"'), true)
  assert.equal(source.includes('class="flex min-w-0 items-center justify-end w-full gap-2"'), true)
  assert.equal(source.includes('class="flex min-w-[11rem] w-full items-center"'), true)
  assert.equal(source.includes('style="max-width: min(34vw, 20rem);"'), true)
  assert.equal(source.includes('FunnelIcon'), true)
  assert.equal(source.includes('max-width: min(24vw, 13.5rem);'), true)
  assert.equal(source.includes('class="input-base h-8 pl-8 pr-2"'), true)
  assert.equal(source.includes('style="background-color: #F5F3EE; border-color: #E5E3DC;"'), true)
  assert.equal(source.includes(`:title="isDeletingArtifact ? 'Deleting table' : 'Delete table'"`), true)
  assert.equal(source.includes(`:title="isDownloading ? 'Exporting CSV' : 'Export CSV'"`), true)
  assert.equal(source.includes('class="btn-icon h-8 w-8 shrink-0 border"'), true)
  assert.equal(source.includes('style="border-color: var(--color-border); color: var(--color-text-muted);"'), true)
})

test('table csv export uses save dialog flow instead of forcing downloads folder', () => {
  const tableTabPath = resolve(process.cwd(), 'src/components/analysis/TableTab.vue')
  const exportUtilPath = resolve(process.cwd(), 'src/utils/exportFile.js')

  const tableTab = readFileSync(tableTabPath, 'utf-8')
  const exportUtil = readFileSync(exportUtilPath, 'utf-8')

  assert.equal(tableTab.includes("import { persistExportFile } from '../../utils/exportFile'"), true)
  assert.equal(tableTab.includes('const exported = await persistExportFile({'), true)
  assert.equal(tableTab.includes("toast.info('Export canceled')"), true)
  assert.equal(tableTab.includes("toast.success('Export complete'"), true)
  assert.equal(exportUtil.includes('window.showSaveFilePicker'), true)
  assert.equal(exportUtil.includes("await import('@tauri-apps/plugin-dialog')"), true)
})
