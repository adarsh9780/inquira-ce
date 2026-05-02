import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import test from 'node:test'

test('profile menu opens as an in-sidebar dropup instead of being clipped outside the rail', () => {
  const testDir = dirname(fileURLToPath(import.meta.url))
  const source = readFileSync(resolve(testDir, '../src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(source.includes('class="absolute bottom-full left-0 z-[var(--z-dropdown)] mb-2 w-52 overflow-hidden rounded-xl border shadow-lg"'), true)
  assert.equal(source.includes('left-full'), false)
})
