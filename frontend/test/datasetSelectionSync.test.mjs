import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('dataset switcher re-syncs non-browser dataset before dispatching refresh event', () => {
  const switcherPath = resolve(process.cwd(), 'src/components/DatasetSwitcher.vue')
  const source = readFileSync(switcherPath, 'utf-8')

  assert.equal(source.includes('await apiService.v1AddDataset(appStore.activeWorkspaceId, ds.file_path)'), true)
  assert.equal(source.includes('selectedTableName = (syncedDataset?.table_name || selectedTableName).trim()'), true)
})
