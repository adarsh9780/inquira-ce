import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('pyodide query bridge includes divide-by-zero guidance in runtime errors', () => {
  const servicePath = resolve(process.cwd(), 'src/services/pyodideService.js')
  const source = readFileSync(servicePath, 'utf-8')

  assert.equal(source.includes('DuckDB query failed:'), true)
  assert.equal(source.includes('NULLIF(denominator, 0)'), true)
})
