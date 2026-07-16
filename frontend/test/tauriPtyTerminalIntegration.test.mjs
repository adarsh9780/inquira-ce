import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('terminal tab routes tauri runtime to xterm-powered PTY pane', () => {
  const terminalTabPath = resolve(process.cwd(), 'src/components/analysis/TerminalTab.vue')
  const source = readFileSync(terminalTabPath, 'utf-8')

  assert.equal(source.includes('v-else-if="useTauriPty"'), true)
  assert.equal(source.includes('<TauriTerminalPane />'), true)
  assert.equal(source.includes("import TauriTerminalPane from './TauriTerminalPane.vue'"), true)
})

test('tauri terminal service invokes native PTY start/write/resize/stop commands', () => {
  const servicePath = resolve(process.cwd(), 'src/services/tauriTerminalService.js')
  const source = readFileSync(servicePath, 'utf-8')

  assert.equal(source.includes("invoke('tauri_terminal_start'"), true)
  assert.equal(source.includes("invoke('tauri_terminal_write'"), true)
  assert.equal(source.includes("invoke('tauri_terminal_resize'"), true)
  assert.equal(source.includes("invoke('tauri_terminal_stop'"), true)
})
