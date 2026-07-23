import test from 'node:test'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('workspace layout keeps only the default split view', () => {
  const layoutUtilityPath = resolve(process.cwd(), 'src/utils/workspaceLayout.js')
  const appSource = readFileSync(resolve(process.cwd(), 'src/App.vue'), 'utf-8')
  const storeSource = readFileSync(resolve(process.cwd(), 'src/stores/appStore.js'), 'utf-8')
  const shortcutsSource = readFileSync(resolve(process.cwd(), 'src/utils/keyboardShortcuts.js'), 'utf-8')
  const panelSource = readFileSync(resolve(process.cwd(), 'src/components/layout/RightPanel.vue'), 'utf-8')

  assert.equal(existsSync(layoutUtilityPath), false)
  assert.equal(appSource.includes('resolveWorkspaceLayoutShortcut'), false)
  assert.equal(storeSource.includes('workspaceLayoutMode'), false)
  assert.equal(storeSource.includes('showLeftPane'), false)
  assert.equal(storeSource.includes('showRightPane'), false)
  assert.equal(shortcutsSource.includes('layout-cycle'), false)
  assert.equal(shortcutsSource.includes('layout-view'), false)
  assert.equal(shortcutsSource.includes('layout-chat'), false)
  assert.equal(shortcutsSource.includes('layout-output'), false)
  assert.equal(panelSource.includes('const leftPaneWidth = computed(() => uiStore.leftPaneWidth)'), true)
  assert.equal(panelSource.includes('const rightPaneWidth = computed(() => 100 - uiStore.leftPaneWidth)'), true)
})
