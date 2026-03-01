import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('top toolbar does not expose shortcuts UI or shortcut kill-switch code', () => {
  const toolbarPath = resolve(process.cwd(), 'src/components/layout/TopToolbar.vue')
  const source = readFileSync(toolbarPath, 'utf-8')

  assert.equal(source.includes('ShortcutsModal'), false)
  assert.equal(source.includes('openShortcuts'), false)
  assert.equal(source.includes('const shortcutsEnabled = false'), false)
})

test('frontend README no longer documents keyboard shortcuts', () => {
  const readmePath = resolve(process.cwd(), 'README.md')
  const source = readFileSync(readmePath, 'utf-8')

  assert.equal(source.includes('Navigation & Shortcuts'), false)
  assert.equal(source.includes('Switch Workspace pane to Chat'), false)
})
