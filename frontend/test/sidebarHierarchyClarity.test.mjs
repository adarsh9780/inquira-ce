import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar communicates active workspace context with conversations and fixed bottom actions', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'),
    'utf-8',
  )

  assert.equal(source.includes('Create/select a workspace first.'), false)
  assert.equal(source.includes('Multiple datasets per workspace.'), false)
  assert.equal(source.includes('Multiple conversations per workspace.'), false)
  assert.equal(source.includes('Open workspace settings'), true)
  assert.equal(source.includes('activeWorkspaceName'), true)
  assert.equal(source.includes('activeWorkspaceCaption'), true)
  assert.equal(source.includes('title="Create Workspace"'), true)
  assert.equal(source.includes('aria-label="Create Workspace"'), true)
  assert.equal(source.includes('ListboxButton'), false)
  assert.equal(source.includes('ListboxOptions'), false)
  assert.equal(source.includes('{{ appStore.workspaces.length }}'), false)
  assert.equal(source.includes('{{ appStore.conversations.length }}'), false)
  assert.equal(source.includes('group-hover:opacity-100'), true)
  assert.equal(source.includes('Datasets</p>'), false)
  assert.equal(source.includes('Conversations'), true)
})

test('global typography uses shared font tokens for consistent UI text styling', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/style.css'), 'utf-8')

  assert.equal(source.includes('--font-ui:'), true)
  assert.equal(source.includes('--font-display:'), true)
  assert.equal(source.includes('font-family: var(--font-ui);'), true)
})
