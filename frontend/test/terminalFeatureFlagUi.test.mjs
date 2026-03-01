import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar only shows terminal icon when terminal feature flag is enabled', () => {
  const sidebarPath = resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue')
  const source = readFileSync(sidebarPath, 'utf-8')

  assert.equal(source.includes('...(appStore.terminalEnabled ? [{'), true)
  assert.equal(source.includes("id: 'terminal'"), true)
})
