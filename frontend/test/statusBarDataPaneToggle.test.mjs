import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('status bar layout button cycles accessible canonical presets', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/StatusBar.vue'), 'utf-8')

  assert.equal(source.includes('@click="appStore.cycleWorkspaceLayoutMode()"'), true)
  assert.equal(source.includes("if (appStore.workspaceLayoutMode === 'chat') return 'Chat'"), true)
  assert.equal(source.includes("if (appStore.workspaceLayoutMode === 'output') return 'Output'"), true)
  assert.equal(source.includes("return 'View'"), true)
  assert.equal(source.includes(':aria-label="workspaceLayoutTitle"'), true)
  assert.equal(source.includes(':aria-keyshortcuts="workspaceLayoutAriaShortcut"'), true)
  assert.equal(source.includes('aria-live="polite"'), true)
})
