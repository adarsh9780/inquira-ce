import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('output renderer shows one selected run with status metadata and no duplicate result cards', () => {
  const outputTabPath = resolve(process.cwd(), 'src/components/analysis/OutputTab.vue')
  const source = readFileSync(outputTabPath, 'utf-8')

  assert.equal(source.includes('Teleport to="#workspace-right-pane-toolbar-right"'), true)
  assert.equal(source.includes("selectedResult.status === 'running'"), true)
  assert.equal(source.includes('Completed with no displayable output.'), true)
  assert.equal(source.includes('selected-result-id'), false)
  assert.equal(source.includes('<HeaderDropdown'), false)
  assert.equal(source.includes('Open in Table tab'), false)
  assert.equal(source.includes('Open in Chart tab'), false)
  assert.equal(source.includes('buildUnifiedResultItems'), true)
})
