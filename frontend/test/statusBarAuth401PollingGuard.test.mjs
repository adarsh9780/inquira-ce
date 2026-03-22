import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('status bar preserves the local session while background auth errors are revalidated', () => {
  const path = resolve(process.cwd(), 'src/components/layout/StatusBar.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('function isUnauthorizedError(error)'), true)
  assert.equal(source.includes('async function handleUnauthorizedPollingError()'), true)
  assert.equal(source.includes("appStore.setRuntimeError('Background auth check failed. Reconnecting your session...')"), true)
  assert.equal(source.includes('await authStore.checkAuth({ preserveSession: true })'), true)
  assert.equal(source.includes('stopArtifactUsageStream()'), true)
  assert.equal(source.includes("settingsWebSocket.setKernelStatusWorkspace('')"), true)
  assert.equal(source.includes('if (isUnauthorizedError(error)) {'), true)
  assert.equal(source.includes('scheduleArtifactUsageReconnect()'), true)
})
