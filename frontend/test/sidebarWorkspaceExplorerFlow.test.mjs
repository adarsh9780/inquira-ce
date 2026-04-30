import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar shows active workspace context with conversations beneath it', () => {
  const unifiedSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'),
    'utf-8',
  )

  // Unified sidebar keeps the single-file implementation
  assert.equal(unifiedSource.includes('SidebarDatasets'), false)
  assert.equal(unifiedSource.includes('SidebarConversations'), false)

  // Workspace context still drives the top section
  assert.equal(unifiedSource.includes('appStore.hasWorkspace'), true)

  // The top section shows workspace details and the conversation list
  assert.equal(unifiedSource.includes('activeWorkspaceName'), true)
  assert.equal(unifiedSource.includes('activeWorkspaceCaption'), true)
  assert.equal(unifiedSource.includes('Open workspace settings'), true)
  assert.equal(unifiedSource.includes('No conversations yet.'), true)
  assert.equal(unifiedSource.includes('Datasets</p>'), false)
})
