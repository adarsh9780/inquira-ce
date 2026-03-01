import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('global keyboard shortcuts are disabled behind a top toolbar kill-switch', () => {
  const toolbarPath = resolve(process.cwd(), 'src/components/layout/TopToolbar.vue')
  const source = readFileSync(toolbarPath, 'utf-8')

  assert.equal(source.includes('const shortcutsEnabled = false'), true)
  assert.equal(source.includes('if (!shortcutsEnabled) {'), true)
})
