import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('status bar no longer exposes alternate layout view controls', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/StatusBar.vue'), 'utf-8')

  assert.equal(source.includes('data-status-view-menu'), false)
  assert.equal(source.includes('role="menuitemradio"'), false)
  assert.equal(source.includes('const layoutPresetOptions = ['), false)
  assert.equal(source.includes('@click="selectLayoutPreset(option.id)"'), false)
  assert.equal(source.includes('WORKSPACE_LAYOUT_MODES'), false)
  assert.equal(source.includes('workspaceLayoutMode'), false)
  assert.equal(source.includes(':aria-keyshortcuts="workspaceLayoutAriaShortcut"'), false)
  assert.equal(source.includes('aria-live="polite"'), false)
  assert.equal(source.includes('class="status-layout-preset"'), false)
  assert.equal(source.includes('status-bar h-7'), true)
  assert.equal(source.includes('text-[11px] font-normal text-[var(--color-text-muted)] select-none'), true)
})
