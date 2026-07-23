import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app store maps persisted code and chat tabs into workspace pane routing', () => {
  const storePath = resolve(process.cwd(), 'src/stores/uiStore.ts')
  const source = readFileSync(storePath, 'utf-8')

  assert.equal(source.includes("const activeTab = ref('workspace')"), true)
  assert.equal(source.includes("const workspacePane = ref('chat')"), true)
  assert.equal(source.includes("const WORKSPACE_PANES = new Set(['code', 'chat'])"), true)
  assert.equal(source.includes("normalized === 'code' || normalized === 'chat' || normalized === 'ctree'"), true)
  assert.equal(source.includes("workspacePane.value = 'ctree'"), false)
  assert.equal(source.includes("workspacePane.value = normalized === 'code' ? 'code' : 'chat'"), true)
  assert.equal(source.includes('normalizeWorkspacePane(pane)'), true)
  assert.equal(source.includes("'conversation-tree'"), true)
  assert.equal(source.includes("activeTab.value = 'workspace'"), true)
})

test('right panel includes unified workspace layout', () => {
  const panelPath = resolve(process.cwd(), 'src/components/layout/RightPanel.vue')
  const source = readFileSync(panelPath, 'utf-8')

  assert.equal(source.includes('WorkspaceLeftPane'), true)
  assert.equal(source.includes('WorkspaceRightPane'), true)
  assert.equal(source.includes("appStore.activeTab === 'workspace'"), true)
  assert.equal(source.includes("appStore.activeTab === 'conversation-tree'"), true)
  assert.equal(source.includes('SidebarGlobalTurnTree'), true)
})

test('preview tab is removed from sidebar navigation and runtime API client', () => {
  const sidebarPath = resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue')
  const sidebarSource = readFileSync(sidebarPath, 'utf-8')
  const apiServicePath = resolve(process.cwd(), 'src/services/apiService.js')
  const apiSource = readFileSync(apiServicePath, 'utf-8')

  assert.equal(sidebarSource.includes("id: 'preview'"), false)
  assert.equal(apiSource.includes('v1GetDatasetPreview('), false)
})
