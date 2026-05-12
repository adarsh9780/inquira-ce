import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar adds a schema entry under workspace and uses numbered conversation badges', () => {
  const sidebarSource = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(sidebarSource.includes('@click="openSchemaEditor"'), true)
  assert.equal(sidebarSource.includes('CircleStackIcon'), true)
  assert.equal(sidebarSource.includes('Schema'), true)
  assert.equal(sidebarSource.includes('Inspect datasets and column metadata'), true)
  assert.equal(sidebarSource.includes('conversationBadgeLabel(index)'), true)
  assert.equal(sidebarSource.includes("if (ordinal > 99) return '99+'"), true)
})

test('activating a conversation returns the shell to workspace chat', () => {
  const storeSource = readFileSync(resolve(process.cwd(), 'src/stores/appStore.js'), 'utf-8')

  assert.equal(storeSource.includes("function setActiveConversationId(conversationId) {"), true)
  assert.equal(storeSource.includes("activeTab.value = 'workspace'"), true)
  assert.equal(storeSource.includes("workspacePane.value = 'chat'"), true)
})
