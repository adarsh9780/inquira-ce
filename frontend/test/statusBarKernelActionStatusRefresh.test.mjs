import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('context bar owns workspace identity while the status bar stays operational', () => {
  const statusPath = resolve(process.cwd(), 'src/components/layout/StatusBar.vue')
  const contextPath = resolve(process.cwd(), 'src/components/layout/WorkspaceContextBar.vue')
  const source = readFileSync(statusPath, 'utf-8')
  const contextSource = readFileSync(contextPath, 'utf-8')

  assert.equal(source.includes('data-workspace-switcher'), false)
  assert.equal(source.includes('{{ activeWorkspaceName }}'), false)
  assert.equal(source.includes('workspaceRuntimeStatusMeta'), true)
  assert.equal(source.includes('Engine {{ workspaceRuntimeStatusMeta.label.toLowerCase() }}'), true)
  assert.equal(source.includes('async function interruptKernel'), false)
  assert.equal(source.includes('async function restartKernel'), false)
  assert.equal(source.includes('Kernel Ready'), false)
  assert.equal(contextSource.includes('data-workspace-context-bar'), true)
  assert.equal(contextSource.includes('{{ activeWorkspaceName }}'), true)
  assert.equal(contextSource.includes('data-action="add-data"'), true)
})
