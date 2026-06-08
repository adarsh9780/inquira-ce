import test from 'node:test'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('backend connection state uses the status bar without the obsolete red alert', () => {
  const appSource = readFileSync(resolve(process.cwd(), 'src/App.vue'), 'utf-8')
  const statusBarSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/StatusBar.vue'),
    'utf-8',
  )

  assert.equal(appSource.includes('ConnectionStatusIndicator'), false)
  assert.equal(
    existsSync(resolve(process.cwd(), 'src/components/ui/ConnectionStatusIndicator.vue')),
    false,
  )
  assert.equal(statusBarSource.includes('settingsWebSocket.onConnection'), true)
  assert.equal(statusBarSource.includes("label: 'Disconnected'"), true)
})

test('frontend connection services omit HTTP readiness polling and legacy websocket APIs', () => {
  const apiSource = readFileSync(resolve(process.cwd(), 'src/services/apiService.js'), 'utf-8')
  const websocketSource = readFileSync(
    resolve(process.cwd(), 'src/services/websocketService.js'),
    'utf-8',
  )

  assert.equal(apiSource.includes('waitForBackendReady'), false)
  assert.equal(apiSource.includes('async healthCheck()'), false)
  assert.equal(websocketSource.includes('onProgress(callback)'), false)
  assert.equal(websocketSource.includes('onComplete(callback)'), false)
  assert.equal(websocketSource.includes('onError(callback)'), false)
  assert.equal(websocketSource.includes('startSettingsSave('), false)
  assert.equal(websocketSource.includes('testHandleMessage('), false)
  assert.equal(websocketSource.includes('maxReconnectAttempts'), false)
  assert.equal(websocketSource.includes('scheduleReconnect()'), true)
})
