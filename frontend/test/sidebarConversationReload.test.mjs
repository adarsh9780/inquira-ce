import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('conversation sidebars reload turns even when the selected conversation is clicked again', () => {
  const compactSidebarSource = readFileSync(resolve(process.cwd(), 'src/components/layout/sidebar/SidebarConversations.vue'), 'utf-8')
  const unifiedSidebarSource = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')
  const compactSelectStart = compactSidebarSource.indexOf('async function selectConversation(id)')
  const compactSelectEnd = compactSidebarSource.indexOf('async function createConversation()', compactSelectStart)
  const compactSelectSource = compactSidebarSource.slice(compactSelectStart, compactSelectEnd)
  const unifiedSelectStart = unifiedSidebarSource.indexOf('async function selectConversation(id)')
  const unifiedSelectEnd = unifiedSidebarSource.indexOf('// ─── Inline title editing', unifiedSelectStart)
  const unifiedSelectSource = unifiedSidebarSource.slice(unifiedSelectStart, unifiedSelectEnd)

  assert.equal(compactSelectSource.includes('if (id !== appStore.activeConversationId) {'), true)
  assert.equal(compactSelectSource.includes('await appStore.fetchConversationTurns({ reset: true })'), true)

  assert.equal(unifiedSelectSource.includes('if (target !== current) {'), true)
  assert.equal(unifiedSelectSource.includes('await appStore.fetchConversationTurns({ reset: true })'), true)
})
