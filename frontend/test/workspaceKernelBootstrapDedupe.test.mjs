import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('workspace kernel bootstrap dedupe is synchronized with shared workspace kernel status', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/stores/appStore.js'),
    'utf-8',
  )

  assert.equal(source.includes('const workspaceKernelStatusById = ref({})'), true)
  assert.equal(source.includes('const activeWorkspaceKernelStatus = computed(() => getWorkspaceKernelStatus())'), true)
  assert.equal(source.includes('function setWorkspaceKernelStatus(workspaceId, status) {'), true)
  assert.equal(source.includes("if (['ready', 'busy', 'starting', 'connecting'].includes(normalizedStatus)) {"), true)
  assert.equal(source.includes("if (normalizedStatus === 'error' || normalizedStatus === 'missing') {"), true)
  assert.equal(source.includes('function getWorkspaceKernelStatus(workspaceId = activeWorkspaceId.value) {'), true)
  assert.equal(source.includes('const ensuredKernelWorkspaceIds = new Set()'), true)
  assert.equal(source.includes('ensuredKernelWorkspaceIds.clear()'), true)
  assert.equal(source.includes('if (ensuredKernelWorkspaceIds.has(targetWorkspaceId)) {'), true)
  assert.equal(source.includes('ensuredKernelWorkspaceIds.add(normalizedWorkspaceId)'), true)
  assert.equal(source.includes('ensuredKernelWorkspaceIds.delete(normalizedWorkspaceId)'), true)
})
