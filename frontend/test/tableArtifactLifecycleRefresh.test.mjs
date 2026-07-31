import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const read = (path) => readFileSync(resolve(process.cwd(), path), 'utf-8')

test('completed chat responses refresh the active turn artifact catalog', () => {
  const chatInput = read('src/components/chat/ChatInput.vue')
  const artifactStore = read('src/stores/artifactStore.ts')

  assert.equal(artifactStore.includes('function requestActiveTurnArtifactRefresh()'), true)
  assert.equal(artifactStore.includes('activeTurnArtifactRefreshKey.value += 1'), true)
  assert.equal(chatInput.includes('artifactStore.requestActiveTurnArtifactRefresh()'), true)
})

test('table artifacts load immediately when returning from another result view', () => {
  const tableTab = read('src/components/analysis/TableTab.vue')
  const lifecycleWatcher = tableTab.slice(
    tableTab.indexOf("String(conversationStore.activeConversationId || '').trim()"),
    tableTab.indexOf('// React to user selecting an artifact'),
  )

  assert.equal(lifecycleWatcher.includes('  },\n  { immediate: true },\n)'), true)
  assert.equal(lifecycleWatcher.includes('await loadActiveTurnArtifacts()'), true)
})
