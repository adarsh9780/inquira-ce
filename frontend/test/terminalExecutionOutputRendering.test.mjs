import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('code execution appends output-style terminal entries (not command entries)', () => {
  const codeTabPath = resolve(process.cwd(), 'src/components/analysis/CodeTab.vue')
  const source = readFileSync(codeTabPath, 'utf-8')

  assert.equal(source.includes("kind: 'output'"), true)
  assert.equal(source.includes('function startRunEntry(scopeLabel, code) {'), true)
  assert.equal(source.includes("command: String(code || '')"), true)
  assert.equal(source.includes('scalarOutputs:'), true)
  assert.equal(source.includes('tableOutputs:'), true)
  assert.equal(source.includes('chartOutputs:'), true)
  assert.equal(source.includes('hasTableOutput:'), true)
  assert.equal(source.includes('hasChartOutput:'), true)
  assert.equal(source.includes('runId'), true)
  assert.equal(source.includes('appStore.updateTerminalEntry'), true)
})
