import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function read(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('workspace pane switchers use the current flat tab treatment instead of white chips', () => {
  const leftPane = read('src/components/layout/WorkspaceLeftPane.vue')
  const rightPane = read('src/components/layout/WorkspaceRightPane.vue')

  assert.equal(leftPane.includes('class="workspace-pane-tab"'), true)
  assert.equal(leftPane.includes('workspace-pane-tab-active'), true)
  assert.equal(leftPane.includes('.workspace-pane-tab-active::after'), true)
  assert.equal(leftPane.includes('background: var(--color-accent);'), true)
  assert.equal(leftPane.includes('transition: color 150ms ease, opacity 150ms ease;'), true)
  assert.equal(leftPane.includes('bg-white shadow-sm'), false)

  assert.equal(rightPane.includes('class="data-pane-tab"'), true)
  assert.equal(rightPane.includes('data-pane-tab-active'), true)
  assert.equal(rightPane.includes('.data-pane-tab-active::after'), true)
  assert.equal(rightPane.includes('background: var(--color-accent);'), true)
  assert.equal(rightPane.includes('transition: color 150ms ease;'), true)
  assert.equal(rightPane.includes('bg-white shadow-sm'), false)
  assert.equal(rightPane.includes('<span class="text-xs font-medium">Table</span>'), true)
  assert.equal(rightPane.includes('<span class="text-xs font-medium">Chart</span>'), true)
  assert.equal(rightPane.includes('<span class="text-xs font-medium">Output</span>'), true)
})
