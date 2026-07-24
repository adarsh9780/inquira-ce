import test from 'node:test'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('native worker connection state stays internal while the status bar surfaces engine state', () => {
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
  assert.equal(statusBarSource.includes('workspaceRuntimeStatusMeta'), true)
  assert.equal(statusBarSource.includes('Engine {{ workspaceRuntimeStatusMeta.label.toLowerCase() }}'), true)
  assert.equal(statusBarSource.includes("label: 'Disconnected'"), false)
  assert.equal(statusBarSource.includes('data-websocket-status'), false)
  assert.equal(statusBarSource.includes('{{ wsConnectionMeta.label }}'), false)
})

test('obsolete connection and standalone feature utilities stay removed', () => {
  const mainSource = readFileSync(resolve(process.cwd(), 'src/main.ts'), 'utf-8')
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
