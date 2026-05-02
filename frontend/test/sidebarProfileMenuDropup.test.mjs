import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import test from 'node:test'

test('profile menu is rendered in a modal dropdown layer with initials badge trigger', () => {
  const testDir = dirname(fileURLToPath(import.meta.url))
  const source = readFileSync(resolve(testDir, '../src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(source.includes('<Teleport to="body">'), true)
  assert.equal(source.includes('class="layer-modal-dropdown fixed overflow-hidden rounded-xl border shadow-lg"'), true)
  assert.equal(source.includes('{{ profileInitials }}'), true)
  assert.equal(source.includes("minWidth: 'var(--size-profile-menu-min-width)'"), true)
  assert.equal(source.includes("top: `calc(${Math.max(0, rect.top)}px - var(--space-overlay-gap))`"), true)
  assert.equal(source.includes('UserCircleIcon'), false)
})
