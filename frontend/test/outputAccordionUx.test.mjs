import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('other output renders a flat execution list with code and output together', () => {
  const outputTabPath = resolve(process.cwd(), 'src/components/analysis/OutputTab.vue')
  const source = readFileSync(outputTabPath, 'utf-8')

  assert.equal(source.includes('Teleport to="#workspace-right-pane-toolbar-right"'), true)
  assert.equal(source.includes('v-for="execution in executionItems"'), true)
  assert.equal(source.includes('data-execution-code'), true)
  assert.equal(source.includes('data-execution-stdout'), true)
  assert.equal(source.includes('data-execution-stderr'), true)
  assert.equal(source.includes('buildOtherExecutionItems'), true)
  assert.equal(source.includes('divide-y'), true)
  assert.equal(source.includes('rounded-xl'), false)
  assert.equal(source.includes('<HeaderDropdown'), false)
  assert.equal(source.includes('Open in Table tab'), false)
  assert.equal(source.includes('Open in Chart tab'), false)
  assert.equal(source.includes('buildUnifiedResultItems'), false)
})
