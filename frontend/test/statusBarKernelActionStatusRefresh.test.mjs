import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('status bar shows workspace switcher and hides advanced runtime actions', () => {
  const path = resolve(process.cwd(), 'src/components/layout/StatusBar.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('data-workspace-switcher'), true)
  assert.equal(source.includes('{{ activeWorkspaceName }}'), true)
  assert.equal(source.includes('workspaceRuntimeStatusMeta'), true)
  assert.equal(source.includes('async function interruptKernel'), false)
  assert.equal(source.includes('async function restartKernel'), false)
  assert.equal(source.includes('Kernel Ready'), false)
})
