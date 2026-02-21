import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('workspace switcher uses modal dialog instead of browser prompt', () => {
  const componentPath = resolve(process.cwd(), 'src/components/WorkspaceSwitcher.vue')
  const source = readFileSync(componentPath, 'utf-8')

  assert.equal(source.includes('window.prompt'), false)
  assert.equal(source.includes('WorkspaceCreateModal'), true)
})
