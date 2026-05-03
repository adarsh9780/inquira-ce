import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import test from 'node:test'

test('profile menu renders from the sidebar bottom nav above collapsed rail clipping', () => {
  const testDir = dirname(fileURLToPath(import.meta.url))
  const source = readFileSync(resolve(testDir, '../src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(source.includes('ref="profileMenuButtonRef"'), true)
  assert.equal(source.includes('<Teleport to="body">'), true)
  assert.equal(source.includes('class="sidebar-profile-menu layer-dropdown fixed w-48 overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-panel-elevated)] shadow-lg"'), true)
  assert.equal(source.includes(':style="profileMenuStyle"'), true)
  assert.equal(source.includes('function updateProfileMenuPosition() {'), true)
  assert.equal(source.includes('sidebar-initials-avatar'), true)
  assert.equal(source.includes('UserCircleIcon'), false)
})
