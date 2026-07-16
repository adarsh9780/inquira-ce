import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('code tab template tells users to wait for the workspace runtime instead of opening a new duckdb connection', () => {
  const codeTabPath = resolve(process.cwd(), 'src/components/analysis/CodeTab.vue')
  const source = readFileSync(codeTabPath, 'utf-8')

  assert.equal(
    source.includes('Workspace runtime connection is not ready. Wait for the workspace to be ready'),
    true,
  )
  assert.equal(
    source.includes('conn = duckdb.connect(r"${dbPath || \'\'}") if "${dbPath || \'\'}".strip() else duckdb.connect()'),
    false,
  )
})
