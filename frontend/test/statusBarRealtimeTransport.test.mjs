import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('status bar uses websocket kernel updates and artifact SSE instead of interval polling', () => {
  const path = resolve(process.cwd(), 'src/components/layout/StatusBar.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('settingsWebSocket.subscribeKernelStatus'), true)
  assert.equal(source.includes('settingsWebSocket.setKernelStatusWorkspace(workspaceId)'), true)
  assert.equal(source.includes('apiService.subscribeWorkspaceArtifactUsage'), true)
  assert.equal(source.includes('function syncWorkspaceRealtimeSubscriptions()'), true)
  assert.equal(source.includes('setInterval(() => {'), false)
})
