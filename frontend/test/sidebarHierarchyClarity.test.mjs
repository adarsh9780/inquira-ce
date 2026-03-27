import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar communicates workspace-first hierarchy and parallel dataset/conversation model', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'),
    'utf-8',
  )

  assert.equal(source.includes('Create/select a workspace first.'), true)
  assert.equal(source.includes('real local folder that stores conversations and datasets'), true)
  assert.equal(source.includes('Multiple datasets per workspace.'), true)
  assert.equal(source.includes('Multiple conversations per workspace.'), true)
  assert.equal(source.includes('FolderOpenIcon v-if="workspacesExpanded"'), true)
  assert.equal(source.includes('FolderOpenIcon v-if="datasetsExpanded"'), true)
  assert.equal(source.includes('FolderOpenIcon v-if="conversationsExpanded"'), true)
  assert.equal(source.includes('title="Create Workspace"'), true)
})

test('global typography uses shared font tokens for consistent UI text styling', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/style.css'), 'utf-8')

  assert.equal(source.includes('--font-ui:'), true)
  assert.equal(source.includes('--font-display:'), true)
  assert.equal(source.includes('font-family: var(--font-ui);'), true)
})
