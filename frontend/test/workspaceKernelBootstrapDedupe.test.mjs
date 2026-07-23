import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('workspace runtime bootstrap dedupe is synchronized with shared workspace runtime status', () => {
  const source = [
    'src/stores/appStore.js',
    'src/stores/executionStore.ts',
  ].map((path) => readFileSync(resolve(process.cwd(), path), 'utf-8')).join('\n')

  assert.match(source, /const workspaceRuntimeStatusById = ref[^(]*\(\{\}\)/)
  assert.equal(source.includes('const activeWorkspaceRuntimeStatus = computed(() => getWorkspaceRuntimeStatus())'), true)
  assert.equal(source.includes('function setWorkspaceRuntimeStatus(workspaceId, status) {'), true)
  assert.equal(source.includes("if (normalizedStatus === 'ready' || normalizedStatus === 'busy') {"), true)
  assert.equal(source.includes("if (['ready', 'busy', 'starting', 'connecting'].includes(normalizedStatus)) {"), false)
  assert.equal(source.includes('function getWorkspaceRuntimeStatus(workspaceId = activeWorkspaceId.value) {'), true)
  assert.equal(source.includes('const ensuredRuntimeWorkspaceIds = new Set()'), true)
  assert.equal(source.includes('ensuredRuntimeWorkspaceIds.clear()'), true)
  assert.equal(source.includes('if (ensuredRuntimeWorkspaceIds.has(targetWorkspaceId)) {'), false)
  assert.equal(source.includes('ensuredRuntimeWorkspaceIds.add(normalizedWorkspaceId)'), true)
  assert.equal(source.includes('ensuredRuntimeWorkspaceIds.delete(normalizedWorkspaceId)'), true)
})
