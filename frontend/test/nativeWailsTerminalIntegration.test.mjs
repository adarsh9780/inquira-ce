import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const read = (path) => readFileSync(resolve(process.cwd(), path), 'utf8')

test('interactive terminal selects the PTY pane in Wails', () => {
  const terminal = read('src/components/analysis/TerminalTab.vue')
  const pane = read('src/components/analysis/NativeTerminalPane.vue')

  assert.equal(terminal.includes('nativeTerminalService.isNativeRuntime()'), true)
  assert.equal(terminal.includes('terminal security policy'), false)
  assert.equal(pane.includes('nativeTerminalService.isNativeRuntime()'), true)
})

test('terminal service routes PTY lifecycle and events through Go', () => {
  const service = read('src/services/nativeTerminalService.js')

  assert.equal(service.includes("requireWailsMethod('StartTerminalSession')"), true)
  assert.equal(service.includes("requireWailsMethod('WriteTerminalSession')"), true)
  assert.equal(service.includes("requireWailsMethod('ResizeTerminalSession')"), true)
  assert.equal(service.includes("requireWailsMethod('StopTerminalSession')"), true)
  assert.equal(service.includes("EventsOn('terminal:pty-data'"), true)
  assert.equal(service.includes("EventsOn('terminal:pty-exit'"), true)
})

test('native terminal availability does not depend on a workspace-path bridge', () => {
  const app = read('../app.go')
  const apiService = read('src/services/apiService.js')

  assert.equal(app.includes('func (a *App) GetWorkspacePaths'), false)
  assert.equal(apiService.includes('v1GetWorkspacePaths'), false)
  assert.equal(apiService.includes("requireWailsMethod('GetWorkspacePaths')"), false)
})
