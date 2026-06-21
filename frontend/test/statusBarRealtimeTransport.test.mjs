import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('status bar uses websocket runtime updates and artifact SSE', () => {
  const path = resolve(process.cwd(), 'src/components/layout/StatusBar.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('settingsWebSocket.subscribeWorkspaceRuntimeStatus'), true)
  assert.equal(source.includes('settingsWebSocket.setWorkspaceRuntimeStatusWorkspace(workspaceId)'), true)
  assert.equal(source.includes('apiService.subscribeWorkspaceArtifactUsage'), true)
  assert.equal(source.includes('function syncWorkspaceRealtimeSubscriptions()'), true)
  assert.equal(source.includes('refreshWorkspaceRuntimeStatusFromApi(workspaceId, \'connecting\')'), true)
})
