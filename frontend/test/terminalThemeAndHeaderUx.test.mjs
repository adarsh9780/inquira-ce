import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('terminal surfaces use shared UI theme tokens instead of hardcoded dark background', () => {
  const terminalTabSource = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/TerminalTab.vue'),
    'utf-8',
  )
  const tauriTerminalSource = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/TauriTerminalPane.vue'),
    'utf-8',
  )

  assert.equal(terminalTabSource.includes('style="background-color: var(--color-base); color: var(--color-text-main);"'), true)
  assert.equal(terminalTabSource.includes('bg-[#0b1228]'), false)

  assert.equal(tauriTerminalSource.includes("style=\"background-color: var(--color-base);\""), true)
  assert.equal(tauriTerminalSource.includes('readThemeColor'), true)
  assert.equal(tauriTerminalSource.includes("background: '#0b1228'"), false)
})

test('terminal header is compact and uses icon controls for session actions', () => {
  const rightPanelSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/RightPanel.vue'),
    'utf-8',
  )
  const terminalTabSource = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/TerminalTab.vue'),
    'utf-8',
  )
  const tauriTerminalSource = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/TauriTerminalPane.vue'),
    'utf-8',
  )

  assert.equal(rightPanelSource.includes('class="flex h-7 justify-between items-center px-3 border-b"'), true)
  assert.equal(rightPanelSource.includes('id="terminal-toolbar" class="flex-1 min-w-0 flex items-center justify-end ml-2 mr-1"'), true)

  assert.equal(terminalTabSource.includes('title="Reset terminal session"'), true)
  assert.equal(terminalTabSource.includes('title="Clear terminal output"'), true)
  assert.equal(terminalTabSource.includes('ArrowPathIcon'), true)
  assert.equal(terminalTabSource.includes('TrashIcon'), true)

  assert.equal(tauriTerminalSource.includes('title="Reset terminal session"'), true)
  assert.equal(tauriTerminalSource.includes('title="Clear terminal output"'), true)
  assert.equal(tauriTerminalSource.includes('ArrowPathIcon'), true)
  assert.equal(tauriTerminalSource.includes('TrashIcon'), true)
})
