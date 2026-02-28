import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('code tab binds Shift+Enter to selected code execution', () => {
  const codeTabPath = resolve(process.cwd(), 'src/components/analysis/CodeTab.vue')
  const source = readFileSync(codeTabPath, 'utf-8')

  assert.equal(source.includes("key: 'Shift-Enter'"), true)
  assert.equal(source.includes('runSelectedCode()'), true)
  assert.equal(source.includes('getSelectedSnippet()'), true)
  assert.equal(source.includes('if (!range.empty)'), true)
  assert.equal(source.includes('editor.state.doc.lineAt(range.head)'), true)
})

test('api service exposes workspace terminal execute endpoint', () => {
  const apiServicePath = resolve(process.cwd(), 'src/services/apiService.js')
  const source = readFileSync(apiServicePath, 'utf-8')

  assert.equal(source.includes('executeTerminalCommand(workspaceId, payload)'), true)
  assert.equal(source.includes('/api/v1/workspaces/${workspaceId}/terminal/execute'), true)
  assert.equal(source.includes('resetTerminalSession(workspaceId)'), true)
  assert.equal(source.includes('/api/v1/workspaces/${workspaceId}/terminal/session/reset'), true)
})
