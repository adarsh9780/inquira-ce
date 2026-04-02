import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('critical workflow mock helper unregisters routes during shutdown', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'e2e/support/criticalWorkflow.js'),
    'utf-8',
  )

  assert.equal(source.includes('const registeredRoutes = []'), true)
  assert.equal(source.includes('await page.unroute(url, handler)'), true)
  assert.equal(source.includes('Ignore shutdown races when the page or browser is already closing.'), true)
  assert.equal(source.includes('return { state, cleanup }'), true)
})

test('critical workflow waits for sidebar preference sync before creating a workspace', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'e2e/support/criticalWorkflow.js'),
    'utf-8',
  )

  assert.equal(source.includes("response.url().includes('/api/v1/preferences')"), true)
  assert.equal(source.includes("response.request().method() === 'PUT'"), true)
  assert.equal(source.includes('await preferenceSync'), true)
  assert.equal(source.includes('const createWorkspaceButton = await openSidebarForWorkspaceCreation(page)'), true)
})
