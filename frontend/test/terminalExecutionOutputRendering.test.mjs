import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('code execution appends output-style terminal entries (not command entries)', () => {
  const codeTabPath = resolve(process.cwd(), 'src/components/analysis/CodeTab.vue')
  const source = readFileSync(codeTabPath, 'utf-8')

  assert.equal(source.includes("kind: 'output'"), true)
  assert.equal(source.includes("label: 'Python output'"), true)
  assert.equal(source.includes('appStore.appendTerminalEntry({'), true)
})

test('terminal tab renders output entries without shell command prompt', () => {
  const terminalPath = resolve(process.cwd(), 'src/components/analysis/TerminalTab.vue')
  const source = readFileSync(terminalPath, 'utf-8')

  assert.equal(source.includes("v-if=\"entry.kind !== 'output'\""), true)
  assert.equal(source.includes('<template v-else>'), true)
  assert.equal(source.includes("{{ entry.label || 'Output' }}"), true)
  assert.equal(source.includes('appStore.clearTerminalEntries()'), true)
})
