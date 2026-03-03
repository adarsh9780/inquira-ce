import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('workspace pane headers use aligned spacing and toolbar offsets', () => {
  const leftPanePath = resolve(process.cwd(), 'src/components/layout/WorkspaceLeftPane.vue')
  const rightPanePath = resolve(process.cwd(), 'src/components/layout/WorkspaceRightPane.vue')

  const leftPane = readFileSync(leftPanePath, 'utf-8')
  const rightPane = readFileSync(rightPanePath, 'utf-8')

  const expectedHeaderClass = 'flex-shrink-0 h-16 border-b px-4 flex items-center gap-4'

  assert.equal(leftPane.includes(expectedHeaderClass), true)
  assert.equal(rightPane.includes(expectedHeaderClass), true)
  assert.equal(rightPane.includes('id="workspace-right-pane-toolbar" class="flex-1 min-w-0 flex items-center justify-end ml-4"'), false)
  assert.equal(rightPane.includes('id="workspace-right-pane-toolbar" class="flex-1 min-w-0 flex items-center justify-end"'), true)
})
