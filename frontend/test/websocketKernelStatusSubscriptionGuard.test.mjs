import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('websocket workspace runtime subscription skips blank workspace ids and duplicate resends', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/services/websocketService.js'),
    'utf-8',
  )

  assert.equal(source.includes('this.lastWorkspaceRuntimeStatusSubscriptionWorkspaceId = \'\''), true)
  assert.equal(source.includes('if (!this.workspaceRuntimeStatusWorkspaceId) {'), true)
  assert.equal(source.includes('if (!workspaceId) return'), true)
  assert.equal(source.includes('if (workspaceId === this.lastWorkspaceRuntimeStatusSubscriptionWorkspaceId) return'), true)
  assert.equal(source.includes("type: 'subscribe_workspace_runtime_status'"), true)
  assert.equal(source.includes('this.lastWorkspaceRuntimeStatusSubscriptionWorkspaceId = workspaceId'), true)
})
