import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import test from 'node:test'

test('profile menu is rendered from the sidebar bottom nav with profile icon trigger', () => {
  const testDir = dirname(fileURLToPath(import.meta.url))
  const source = readFileSync(resolve(testDir, '../src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(source.includes('ref="profileMenuButtonRef"'), true)
  assert.equal(source.includes('class="profile-menu absolute bottom-0 left-full z-[var(--z-dropdown)] ml-2 w-48 overflow-hidden rounded-xl border shadow-lg"'), true)
  assert.equal(source.includes('data-profile-menu'), true)
  assert.equal(source.includes('UserCircleIcon'), true)
  assert.equal(source.includes('<Teleport to="body">'), false)
})
