import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar communicates workspace-first hierarchy and parallel dataset/conversation model', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'),
    'utf-8',
  )

  assert.equal(source.includes('Create or choose one workspace first.'), true)
  assert.equal(source.includes('Each workspace contains its own datasets and conversations.'), true)
  assert.equal(source.includes('Multiple datasets can exist in one workspace.'), true)
  assert.equal(source.includes('Conversations are separate from datasets in this workspace.'), true)
  assert.equal(source.includes('Step 1'), true)
  assert.equal(source.includes('Step 2'), true)
  assert.equal(source.includes('Step 3'), true)
})

test('global typography uses shared font tokens for consistent UI text styling', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/style.css'), 'utf-8')

  assert.equal(source.includes('--font-ui:'), true)
  assert.equal(source.includes('--font-display:'), true)
  assert.equal(source.includes('font-family: var(--font-ui);'), true)
})
