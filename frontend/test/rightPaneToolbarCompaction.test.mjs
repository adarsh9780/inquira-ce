import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('figure toolbar keeps a contextual artifact selector and icon actions', () => {
  const figureTabPath = resolve(process.cwd(), 'src/components/analysis/FigureTab.vue')
  const source = readFileSync(figureTabPath, 'utf-8')

  assert.equal(source.includes('to="#workspace-right-pane-toolbar-center"'), true)
  assert.equal(source.includes('<HeaderDropdown'), true)
  assert.equal(source.includes("label: 'Delete chart'"), true)
  assert.equal(source.includes(`:title="isDownloading ? 'Exporting chart' : 'Export chart'"`), true)
  assert.equal(source.includes('ChevronDownIcon'), false)
  assert.equal(source.includes('class="btn-icon h-8 w-8 shrink-0 border"'), true)
  assert.equal(source.includes('style="border-color: var(--color-border); color: var(--color-text-muted);"'), true)
})

test('runs toolbar shows a compact execution count without another result filter', () => {
  const outputTabPath = resolve(process.cwd(), 'src/components/analysis/OutputTab.vue')
  const source = readFileSync(outputTabPath, 'utf-8')

  assert.equal(source.includes("executionItems.length === 1 ? 'run' : 'runs'"), true)
  assert.equal(source.includes('outputSummary'), true)
  assert.equal(source.includes('formatTimestamp'), true)
  assert.equal(source.includes('FunnelIcon'), false)
  assert.equal(source.includes('<HeaderDropdown'), false)
})
