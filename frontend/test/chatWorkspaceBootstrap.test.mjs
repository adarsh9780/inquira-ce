import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat input requires active workspace before submit and does not auto-create one', () => {
  const componentPath = resolve(process.cwd(), 'src/components/chat/ChatInput.vue')
  const source = readFileSync(componentPath, 'utf-8')

  assert.equal(source.includes('async function ensureWorkspaceForChat()'), false)
  assert.equal(source.includes("const workspaceId = appStore.activeWorkspaceId"), true)
  assert.equal(source.includes("throw new Error('Create/select a workspace before analysis.')"), true)
  assert.equal(source.includes('await ensureWorkspaceDatasetReady(workspaceId)'), true)
  assert.equal(source.includes('workspace_id: workspaceId'), true)
  assert.equal(source.includes("Create or select a workspace from the header dropdown"), true)
})
