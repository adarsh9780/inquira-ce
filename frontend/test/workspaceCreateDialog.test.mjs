import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('workspace switcher routes new workspace action through unified workspace settings', () => {
  const componentPath = resolve(process.cwd(), 'src/components/WorkspaceSwitcher.vue')
  const source = readFileSync(componentPath, 'utf-8')

  assert.equal(source.includes('window.prompt'), false)
  assert.equal(source.includes('WorkspaceCreateModal'), false)
  assert.equal(source.includes("appStore.openSettings('workspace')"), true)
  assert.equal(source.includes('settingsInitialStep'), false)
})
