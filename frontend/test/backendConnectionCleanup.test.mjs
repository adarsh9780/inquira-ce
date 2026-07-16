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
  assert.equal(statusBarSource.includes('data-websocket-status'), true)
  assert.equal(statusBarSource.includes('{{ wsConnectionMeta.label }}'), true)
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

test('obsolete connection and standalone feature utilities stay removed', () => {
  const mainSource = readFileSync(resolve(process.cwd(), 'src/main.js'), 'utf-8')
  const removedPaths = [
    'public/human-body-facts.json',
    'src/components/chat/TurnViewer.vue',
    'src/components/modals/tabs/TermsTab.vue',
    'src/services/factService.js',
    'src/utils/fileHandleSupport.js',
    'src/utils/runtimeGate.js',
    'src/utils/streamingCapability.js',
    'src/utils/tableSelection.js',
    'src/utils/websocketTest.js',
  ]

  assert.equal(mainSource.includes('websocketTest'), false)
  removedPaths.forEach((path) => {
    assert.equal(existsSync(resolve(process.cwd(), path)), false, `${path} should remain removed`)
  })
})
