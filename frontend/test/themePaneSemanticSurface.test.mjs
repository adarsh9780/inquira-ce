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
  const styles = read('src/style.css')

  assert.equal(leftPane.includes('<SegmentedControl'), true)
  assert.equal(leftPane.includes('bg-white shadow-sm'), false)

  assert.equal(rightPane.includes('<SegmentedControl'), true)
  assert.equal(rightPane.includes('bg-white shadow-sm'), false)
  assert.equal(styles.includes('.segmented-control-item-active'), true)
  assert.equal(styles.includes('background: var(--color-selected-surface);'), true)
})
