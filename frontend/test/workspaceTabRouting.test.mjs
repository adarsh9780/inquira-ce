import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app store maps legacy code/chat tabs into workspace pane routing', () => {
  const storePath = resolve(process.cwd(), 'src/stores/appStore.js')
  const source = readFileSync(storePath, 'utf-8')

  assert.equal(source.includes("const activeTab = ref('workspace')"), true)
  assert.equal(source.includes("const workspacePane = ref('code')"), true)
  assert.equal(source.includes("if (normalized === 'code')"), true)
  assert.equal(source.includes("if (normalized === 'chat')"), true)
  assert.equal(source.includes("activeTab.value = 'workspace'"), true)
})

test('right panel includes unified workspace tab component', () => {
  const panelPath = resolve(process.cwd(), 'src/components/layout/RightPanel.vue')
  const source = readFileSync(panelPath, 'utf-8')

  assert.equal(source.includes('WorkspaceTab'), true)
  assert.equal(source.includes("id: 'workspace'"), true)
  assert.equal(source.includes("appStore.activeTab === 'workspace'"), true)
  assert.equal(source.includes('Chat Overlay'), false)
})
