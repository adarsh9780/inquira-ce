import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('conversation sidebars reload turns even when the selected conversation is clicked again', () => {
  const compactSidebarSource = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')
  const globalTreeSource = readFileSync(resolve(process.cwd(), 'src/components/layout/sidebar/SidebarGlobalTurnTree.vue'), 'utf-8')
  const compactSelectStart = compactSidebarSource.indexOf('async function selectConversation(id)')
  const compactSelectEnd = compactSidebarSource.indexOf('// ─── Inline title editing', compactSelectStart)
  const compactSelectSource = compactSidebarSource.slice(compactSelectStart, compactSelectEnd)

  assert.equal(compactSelectSource.includes('if (target !== current) {'), true)
  assert.equal(compactSelectSource.includes('await appStore.fetchConversationTurns({ reset: true, preferLatest: true })'), true)

  assert.equal(globalTreeSource.includes('if (targetConversationId !== appStore.activeConversationId) {'), true)
  assert.equal(globalTreeSource.includes('await appStore.fetchConversationTurns({ reset: true })'), true)
})
