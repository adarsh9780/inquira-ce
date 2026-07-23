import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app store derives data readiness from the active workspace summary', () => {
  const storePath = resolve(process.cwd(), 'src/stores/appStore.js')
  const source = readFileSync(storePath, 'utf-8')

  assert.equal(source.includes('dataFilePath'), false)
  assert.equal(source.includes('ingestedTableName'), false)
  assert.equal(source.includes('ingestedColumns'), false)
  assert.equal(source.includes('const tableCount = Number(activeWorkspaceSummary.value?.table_count || 0)'), true)
  assert.equal(source.includes("if (tableCount < 1) return { state: 'no_data', ready: false }"), true)
})
