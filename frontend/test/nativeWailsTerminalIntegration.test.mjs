import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const read = (path) => readFileSync(resolve(process.cwd(), path), 'utf8')

test('interactive terminal selects the PTY pane in Wails', () => {
  const terminal = read('src/components/analysis/TerminalTab.vue')
  const pane = read('src/components/analysis/TauriTerminalPane.vue')

  assert.equal(terminal.includes('tauriTerminalService.isNativeRuntime()'), true)
  assert.equal(pane.includes('tauriTerminalService.isNativeRuntime()'), true)
})

test('terminal service routes PTY lifecycle and events through Go', () => {
  const service = read('src/services/tauriTerminalService.js')

  assert.equal(service.includes('app?.StartTerminalSession'), true)
  assert.equal(service.includes('app.WriteTerminalSession('), true)
  assert.equal(service.includes('app.ResizeTerminalSession('), true)
  assert.equal(service.includes('app.StopTerminalSession('), true)
  assert.equal(service.includes("EventsOn('terminal:pty-data'"), true)
  assert.equal(service.includes("EventsOn('terminal:pty-exit'"), true)
})

test('workspace paths advertise native terminal availability', () => {
  const app = read('../app.go')

  assert.equal(app.includes('TerminalEnabled:    true'), true)
})
