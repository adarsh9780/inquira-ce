import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'
import assert from 'node:assert/strict'

test('unified sidebar keeps the current compact workspace and chat layout', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(source.includes('class="relative z-40 flex h-full w-full min-h-0 min-w-0 flex-col overflow-hidden sidebar-root"'), true)
  assert.equal(source.includes('activeWorkspaceCaption'), true)
  assert.equal(source.includes('Chats'), true)
  assert.equal(source.includes('sidebar-initials-avatar'), true)
  assert.equal(source.includes('UserCircleIcon'), false)
  assert.equal(source.includes('sidebar-brand-toggle'), false)
})
