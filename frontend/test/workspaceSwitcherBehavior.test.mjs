import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('workspace switcher does not auto-create a default workspace on mount', () => {
  const componentPath = resolve(process.cwd(), 'src/components/WorkspaceSwitcher.vue')
  const source = readFileSync(componentPath, 'utf-8')

  assert.equal(
    source.includes("createWorkspace('Default Workspace')"),
    false,
    'WorkspaceSwitcher should not auto-create a default workspace'
  )
})
