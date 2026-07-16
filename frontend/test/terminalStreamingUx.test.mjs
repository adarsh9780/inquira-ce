import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('terminal tab consumes streaming terminal API events for live output', () => {
  const terminalPath = resolve(process.cwd(), 'src/components/analysis/TerminalTab.vue')
  const source = readFileSync(terminalPath, 'utf-8')

  assert.equal(source.includes('executeTerminalCommandStream('), true)
  assert.equal(source.includes("evt?.event === 'output'"), true)
  assert.equal(source.includes('liveStdout.value = liveStdout.value ?'), true)
  assert.equal(source.includes("v-if=\"isRunning && liveCommand\""), true)
})
