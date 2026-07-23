import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('terminal surfaces use shared UI theme tokens instead of hardcoded dark background', () => {
  const nativeTerminalSource = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/NativeTerminalPane.vue'),
    'utf-8',
  )

  assert.equal(nativeTerminalSource.includes("style=\"background-color: var(--color-base);\""), true)
  assert.equal(nativeTerminalSource.includes('readThemeColor'), true)
  assert.equal(nativeTerminalSource.includes("background: '#0b1228'"), false)
})

test('terminal header is compact and uses icon controls for session actions', () => {
  const rightPanelSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/RightPanel.vue'),
    'utf-8',
  )
  const nativeTerminalSource = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/NativeTerminalPane.vue'),
    'utf-8',
  )

  assert.equal(rightPanelSource.includes('class="flex h-7 justify-between items-center px-3 border-b"'), true)
  assert.equal(rightPanelSource.includes('id="terminal-toolbar" class="flex-1 min-w-0 flex items-center justify-end ml-2 mr-1"'), true)

  assert.equal(nativeTerminalSource.includes('title="Reset terminal session"'), true)
  assert.equal(nativeTerminalSource.includes('title="Clear terminal output"'), true)
  assert.equal(nativeTerminalSource.includes('ArrowPathIcon'), true)
  assert.equal(nativeTerminalSource.includes('TrashIcon'), true)
})
