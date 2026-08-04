import test from 'node:test'
import assert from 'node:assert/strict'
import { resolve } from 'node:path'

import { readFileSync } from './sourceText.mjs'

test('results toolbar derives safe modes from the actual pane width', () => {
  const pane = readFileSync(resolve(process.cwd(), 'src/components/layout/WorkspaceRightPane.vue'), 'utf8')
  const segmented = readFileSync(resolve(process.cwd(), 'src/components/ui/SegmentedControl.vue'), 'utf8')

  assert.match(pane, /const paneWidth = ref\(0\)/)
  assert.match(pane, /if \(paneWidth\.value >= 900\) return 'wide'/)
  assert.match(pane, /if \(paneWidth\.value >= 520\) return 'compact'/)
  assert.match(pane, /return 'minimal'/)
  assert.match(pane, /:icon-only="toolbarMode !== 'wide'"/)
  assert.match(pane, /<TableTab[^>]*:toolbar-mode="toolbarMode"/)
  assert.match(pane, /<FigureTab[^>]*:toolbar-mode="toolbarMode"/)
  assert.match(pane, /<OutputTab[^>]*:toolbar-mode="toolbarMode"/)
  assert.match(segmented, /:data-icon-only="iconOnly \|\| undefined"/)
})

test('workspace shell starts compact and expands controls only after measurement', () => {
  const panel = readFileSync(resolve(process.cwd(), 'src/components/layout/RightPanel.vue'), 'utf8')
  const context = readFileSync(resolve(process.cwd(), 'src/components/layout/WorkspaceContextBar.vue'), 'utf8')

  assert.match(panel, /const isCompactLayout = ref\(true\)/)
  assert.match(panel, /<WorkspaceContextBar :compact="isCompactLayout"/)
  assert.match(context, /workspaceStore\.hasWorkspace && !compact/)
  assert.match(context, /conversationStore\.activeTurnId && !compact/)
})
