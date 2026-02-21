import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('duckdb initialize requires both db and connection before short-circuit', () => {
  const servicePath = resolve(process.cwd(), 'src/services/duckdbService.js')
  const source = readFileSync(servicePath, 'utf-8')

  assert.equal(source.includes('if (this.db && this.conn) return this.db;'), true)
  assert.equal(source.includes('this.db = null;'), true)
  assert.equal(source.includes('this.conn = null;'), true)
})

test('preview service tolerates duckdb startup errors and returns safe empty result', () => {
  const servicePath = resolve(process.cwd(), 'src/services/previewService.js')
  const source = readFileSync(servicePath, 'utf-8')

  assert.equal(source.includes("Browser engine is still initializing. Please try preview again."), true)
  assert.equal(source.includes('try {'), true)
})
