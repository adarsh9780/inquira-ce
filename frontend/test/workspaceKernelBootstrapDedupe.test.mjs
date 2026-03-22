import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('workspace kernel bootstrap is only performed once per workspace until auth state resets', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/stores/appStore.js'),
    'utf-8',
  )

  assert.equal(source.includes('const ensuredKernelWorkspaceIds = new Set()'), true)
  assert.equal(source.includes('ensuredKernelWorkspaceIds.clear()'), true)
  assert.equal(source.includes('if (ensuredKernelWorkspaceIds.has(targetWorkspaceId)) {'), true)
  assert.equal(source.includes('ensuredKernelWorkspaceIds.add(targetWorkspaceId)'), true)
  assert.equal(source.includes('ensuredKernelWorkspaceIds.delete(targetWorkspaceId)'), true)
})
