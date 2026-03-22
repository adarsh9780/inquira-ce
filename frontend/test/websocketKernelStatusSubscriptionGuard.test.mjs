import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('websocket kernel status subscription skips blank workspace ids and duplicate resends', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/services/websocketService.js'),
    'utf-8',
  )

  assert.equal(source.includes('this.lastKernelStatusSubscriptionWorkspaceId = \'\''), true)
  assert.equal(source.includes('if (!this.kernelStatusWorkspaceId) {'), true)
  assert.equal(source.includes('if (!workspaceId) return'), true)
  assert.equal(source.includes('if (workspaceId === this.lastKernelStatusSubscriptionWorkspaceId) return'), true)
  assert.equal(source.includes('this.lastKernelStatusSubscriptionWorkspaceId = workspaceId'), true)
})
