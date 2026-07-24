import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

const root = process.cwd()
const read = (path) => readFileSync(resolve(root, path), 'utf8')

test('frontend uses six typed domain stores without a compatibility facade', () => {
  assert.equal(existsSync(resolve(root, 'src/stores/appStore.js')), false)
  for (const name of ['ui', 'preferences', 'artifact', 'execution', 'workspace', 'conversation']) {
    const source = read(`src/stores/${name}Store.ts`)
    assert.match(source, /defineStore\(/)
  }
})

test('cross-domain state workflows live in coordinators', () => {
  const snapshot = read('src/composables/useSessionSnapshot.ts')
  const activation = read('src/composables/useWorkspaceActivation.ts')
  assert.match(snapshot, /SNAPSHOT_VERSION/)
  assert.doesNotMatch(snapshot, /apiKey:/)
  assert.match(activation, /workspaceReadiness/)
  assert.match(activation, /clearWorkspaceSession/)
})

test('production source has no compatibility-store imports', () => {
  for (const path of [
    'src/App.vue',
    'src/components/chat/ChatInput.vue',
    'src/components/chat/ChatHistory.vue',
    'src/components/layout/UnifiedSidebar.vue',
    'src/components/modals/tabs/WorkspaceTab.vue',
  ]) {
    assert.doesNotMatch(read(path), /useAppStore|stores\/appStore/)
  }
})
