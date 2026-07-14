import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('workspace pane headers use aligned spacing and toolbar offsets', () => {
  const leftPanePath = resolve(process.cwd(), 'src/components/layout/WorkspaceLeftPane.vue')
  const rightPanePath = resolve(process.cwd(), 'src/components/layout/WorkspaceRightPane.vue')

  const leftPane = readFileSync(leftPanePath, 'utf-8')
  const rightPane = readFileSync(rightPanePath, 'utf-8')

  assert.equal(leftPane.includes('<AppToolbar'), true)
  assert.equal(rightPane.includes('<AppToolbar'), true)
  assert.equal(rightPane.includes('id="workspace-right-pane-toolbar"'), false)
  assert.equal(rightPane.includes('id="workspace-right-pane-toolbar-center"'), true)
  assert.equal(rightPane.includes('id="workspace-right-pane-toolbar-right"'), true)
  assert.equal(rightPane.includes('class="workspace-toolbar-divider"'), false)
  assert.equal(rightPane.includes('workspace-toolbar-divider'), false)
})
