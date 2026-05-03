import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar communicates active workspace context, chats, and bottom actions', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(source.includes('Open workspace settings'), true)
  assert.equal(source.includes('activeWorkspaceName'), true)
  assert.equal(source.includes('activeWorkspaceCaption'), true)
  assert.equal(source.includes('Chats'), true)
  assert.equal(source.includes('Profile Settings'), true)
  assert.equal(source.includes('Datasets</p>'), false)
  assert.equal(source.includes('ListboxButton'), false)
})

test('global typography still uses shared font tokens', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/style.css'), 'utf-8')

  assert.equal(source.includes('--font-ui:'), true)
  assert.equal(source.includes('--font-display:'), true)
  assert.equal(source.includes('font-family: var(--font-ui);'), true)
})
