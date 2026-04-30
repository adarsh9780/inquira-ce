import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function read(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('workspace pane switchers use semantic selected surfaces instead of white chips', () => {
  const leftPane = read('src/components/layout/WorkspaceLeftPane.vue')
  const rightPane = read('src/components/layout/WorkspaceRightPane.vue')

  assert.equal(leftPane.includes('background-color: var(--color-control-surface);'), true)
  assert.equal(leftPane.includes('background-color: var(--color-selected-surface);'), true)
  assert.equal(leftPane.includes('box-shadow: inset 0 0 0 1px var(--color-selected-border);'), true)
  assert.equal(leftPane.includes('bg-white shadow-sm'), false)

  assert.equal(rightPane.includes('background-color: var(--color-control-surface);'), true)
  assert.equal(rightPane.includes('background-color: var(--color-selected-surface);'), true)
  assert.equal(rightPane.includes('box-shadow: inset 0 0 0 1px var(--color-selected-border);'), true)
  assert.equal(rightPane.includes('bg-white shadow-sm'), false)
  assert.equal(rightPane.includes('<span class="text-xs font-medium">Table</span>'), true)
  assert.equal(rightPane.includes('<span class="text-xs font-medium">Chart</span>'), true)
  assert.equal(rightPane.includes('<span class="text-xs font-medium">Output</span>'), true)
})
