import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('workspace right pane routes third icon tab to output panel', () => {
  const rightPanePath = resolve(process.cwd(), 'src/components/layout/WorkspaceRightPane.vue')
  const source = readFileSync(rightPanePath, 'utf-8')

  assert.equal(source.includes("appStore.setDataPane('output')"), true)
  assert.equal(source.includes("appStore.dataPane === 'output'"), true)
  assert.equal(source.includes("title=\"Output\""), true)
  assert.equal(source.includes('<OutputTab />'), true)
})

test('output panel shows filtered analysis stdout/stderr entries', () => {
  const outputTabPath = resolve(process.cwd(), 'src/components/analysis/OutputTab.vue')
  const source = readFileSync(outputTabPath, 'utf-8')

  assert.equal(source.includes("entry?.kind === 'output' && entry?.source === 'analysis'"), true)
  assert.equal(source.includes("{ value: 'all', label: 'All' }"), true)
  assert.equal(source.includes("{ value: 'stdout', label: 'stdout' }"), true)
  assert.equal(source.includes("{ value: 'stderr', label: 'stderr' }"), true)
})

test('code execution routes runtime errors to output pane', () => {
  const codeTabPath = resolve(process.cwd(), 'src/components/analysis/CodeTab.vue')
  const source = readFileSync(codeTabPath, 'utf-8')

  assert.equal(source.includes("appStore.setActiveTab('output')"), true)
  assert.equal(source.includes('else if (outputStdout || outputStderr)'), true)
})
