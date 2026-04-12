import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('workspace pane headers use aligned spacing and toolbar offsets', () => {
  const leftPanePath = resolve(process.cwd(), 'src/components/layout/WorkspaceLeftPane.vue')
  const rightPanePath = resolve(process.cwd(), 'src/components/layout/WorkspaceRightPane.vue')

  const leftPane = readFileSync(leftPanePath, 'utf-8')
  const rightPane = readFileSync(rightPanePath, 'utf-8')

  const leftHeaderClass = 'flex-shrink-0 h-16 px-4 flex items-center gap-4'
  const rightHeaderClass = 'workspace-toolbar-shell flex-shrink-0 h-16 px-3 flex items-center border-b'

  assert.equal(leftPane.includes(leftHeaderClass), true)
  assert.equal(rightPane.includes(rightHeaderClass), true)
  assert.equal(rightPane.includes('id="workspace-right-pane-toolbar"'), false)
  assert.equal(rightPane.includes('id="workspace-right-pane-toolbar-center"'), true)
  assert.equal(rightPane.includes('id="workspace-right-pane-toolbar-right"'), true)
  assert.equal(rightPane.includes('class="workspace-toolbar-divider"'), true)
})
