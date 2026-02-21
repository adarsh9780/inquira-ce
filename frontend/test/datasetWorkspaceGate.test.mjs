import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('dataset switcher is disabled when no workspace exists', () => {
  const componentPath = resolve(process.cwd(), 'src/components/DatasetSwitcher.vue')
  const source = readFileSync(componentPath, 'utf-8')

  assert.equal(source.includes(':disabled="loading || !appStore.hasWorkspace"'), true)
  assert.equal(source.includes("Select Workspace First"), true)
})

test('app store clears stale dataset state when workspace list is empty', () => {
  const storePath = resolve(process.cwd(), 'src/stores/appStore.js')
  const source = readFileSync(storePath, 'utf-8')

  assert.equal(source.includes('if (items.length === 0 && (dataFilePath.value || ingestedTableName.value || schemaFileId.value))'), true)
  assert.equal(source.includes("dataFilePath.value = ''"), true)
  assert.equal(source.includes("ingestedTableName.value = ''"), true)
})
