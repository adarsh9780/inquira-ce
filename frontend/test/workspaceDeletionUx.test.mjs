import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('workspace switcher uses confirmation modal for deletion instead of window.confirm', () => {
  const componentPath = resolve(process.cwd(), 'src/components/WorkspaceSwitcher.vue')
  const source = readFileSync(componentPath, 'utf-8')

  assert.equal(source.includes('ConfirmationModal'), true)
  assert.equal(source.includes('window.confirm'), false)
})

test('workspace switcher includes deleting status row in dropdown', () => {
  const componentPath = resolve(process.cwd(), 'src/components/WorkspaceSwitcher.vue')
  const source = readFileSync(componentPath, 'utf-8')

  assert.equal(source.includes('Deleting...'), true)
  assert.equal(source.includes('workspaceDeletionJobs'), true)
})
