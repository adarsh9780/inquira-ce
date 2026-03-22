import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('clicking the active conversation keeps the sidebar open', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/layout/sidebar/SidebarConversations.vue'),
    'utf-8',
  )

  assert.equal(source.includes('if (id === appStore.activeConversationId) {'), true)
  assert.equal(source.includes('appStore.setSidebarCollapsed(true)'), false)
  assert.equal(source.includes("emit('select')"), true)
})
