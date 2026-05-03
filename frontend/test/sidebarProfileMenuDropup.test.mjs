import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import test from 'node:test'

test('profile menu renders from the sidebar bottom nav with a local dropup', () => {
  const testDir = dirname(fileURLToPath(import.meta.url))
  const source = readFileSync(resolve(testDir, '../src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(source.includes('ref="profileMenuButtonRef"'), true)
  assert.equal(source.includes('class="absolute bottom-full left-0 mb-2 z-50 w-48 overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-panel-elevated)] shadow-lg"'), true)
  assert.equal(source.includes('UserCircleIcon'), true)
  assert.equal(source.includes('<Teleport to="body">'), false)
})
