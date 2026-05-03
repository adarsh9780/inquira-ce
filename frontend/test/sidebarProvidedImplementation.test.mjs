import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'
import assert from 'node:assert/strict'

test('unified sidebar uses the provided compact workspace and chat layout', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'),
    'utf-8',
  )

  assert.equal(source.includes('class="relative z-40 flex h-full min-h-0 shrink-0 flex-col overflow-hidden sidebar-root"'), true)
  assert.equal(source.includes('activeWorkspaceCaption'), true)
  assert.equal(source.includes('>Chats</span>'), true)
  assert.equal(source.includes('class="nav-btn"'), true)
  assert.equal(source.includes('UserCircleIcon'), true)
  assert.equal(source.includes('sidebar-brand-toggle'), false)
})
