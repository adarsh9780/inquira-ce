import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const source = fs.readFileSync(path.join(root, 'src/services/apiService.js'), 'utf8')

test('catalog schemas and runtime readiness use Wails in native mode', () => {
  for (const method of ['ListWorkspaceDatasets', 'GetWorkspaceDatasetSchema', 'SaveWorkspaceDatasetSchema', 'GetWorkspaceKernelStatus']) {
    assert.match(source, new RegExp(`requireWailsMethod\\('${method}'\\)`))
  }
})

test('manual Code-tab execution uses the persisted native run API', () => {
  assert.match(source, /requireWailsMethod\('RunManualCode'\)/)
  assert.match(source, /conversation_id/)
  assert.match(source, /parent_turn_id/)
})

test('schema regeneration uses the native generator', () => {
  assert.match(source, /requireWailsMethod\('RegenerateWorkspaceDatasetSchema'\)/)
  assert.doesNotMatch(source, /AI schema regeneration has not been migrated/)
})
