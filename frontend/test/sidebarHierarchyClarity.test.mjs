import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar communicates workspace-first hierarchy and parallel dataset/conversation model', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'),
    'utf-8',
  )

  assert.equal(source.includes('Create/select a workspace first.'), false)
  assert.equal(source.includes('Multiple datasets per workspace.'), false)
  assert.equal(source.includes('Multiple conversations per workspace.'), false)
  assert.equal(source.includes('FolderOpenIcon v-if="workspacesExpanded"'), true)
  assert.equal(source.includes('FolderOpenIcon v-if="datasetsExpanded"'), true)
  assert.equal(source.includes('FolderOpenIcon v-if="conversationsExpanded"'), true)
  assert.equal(source.includes('title="Create Workspace"'), true)
  assert.equal(source.includes('{{ appStore.workspaces.length }}'), false)
  assert.equal(source.includes('{{ appStore.conversations.length }}'), false)
})

test('global typography uses shared font tokens for consistent UI text styling', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/style.css'), 'utf-8')

  assert.equal(source.includes('--font-ui:'), true)
  assert.equal(source.includes('--font-display:'), true)
  assert.equal(source.includes('font-family: var(--font-ui);'), true)
})
