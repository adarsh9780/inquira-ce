import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

test('code and terminal surfaces disclose the local unsandboxed execution boundary', () => {
  const codeTab = fs.readFileSync(path.resolve('src/components/analysis/CodeTab.vue'), 'utf8')
  const terminalTab = fs.readFileSync(path.resolve('src/components/analysis/TerminalTab.vue'), 'utf8')

  assert.equal(codeTab.includes('Python runs locally with your user permissions and is not sandboxed.'), true)
  assert.equal(terminalTab.includes('Terminal execution is not sandboxed.'), true)
})
