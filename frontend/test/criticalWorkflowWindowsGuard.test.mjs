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
  assert.equal(source.includes('function isIgnorableRouteError(error)'), true)
  assert.equal(source.includes("message.includes('Route is already handled!')"), true)
  assert.equal(source.includes('async function fetchRouteResponse(route)'), true)
  assert.equal(source.includes('async function fulfillRoute(route, payload)'), true)
  assert.equal(source.includes('await page.unroute(url, handler)'), true)
  assert.equal(source.includes("await page.unrouteAll({ behavior: 'ignoreErrors' })"), true)
  assert.equal(source.includes('Ignore shutdown races when the page or browser is already closing.'), true)
  assert.equal(source.includes('return { state, cleanup }'), true)
})

test('critical workflow waits for sidebar preference sync before creating a workspace', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'e2e/support/criticalWorkflow.js'),
    'utf-8',
  )

  assert.equal(source.includes("if (!(await createWorkspaceButton.isVisible().catch(() => false))) {"), true)
  assert.equal(source.includes("await clickWhenReady(page, toggle, { timeout: 15_000 })"), true)
  assert.equal(source.includes("response.url().includes('/api/v1/preferences')"), true)
  assert.equal(source.includes("response.request().method() === 'PUT'"), true)
  assert.equal(source.includes('await preferenceSync'), true)
  assert.equal(source.includes('const createWorkspaceButton = await openSidebarForWorkspaceCreation(page)'), true)
})

test('critical workflow waits for the startup overlay to clear before clicking through setup', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'e2e/support/criticalWorkflow.js'),
    'utf-8',
  )

  assert.equal(source.includes("page.getByTestId('startup-overlay')"), true)
  assert.equal(source.includes("toHaveAttribute('data-active', 'false'"), true)
  assert.equal(source.includes('async function clickWhenReady(page, locator, options = {})'), true)
  assert.equal(source.includes('const readinessTimeout = Number.isFinite(options.readinessTimeout) ? options.readinessTimeout : 90_000'), true)
  assert.equal(source.includes('intercepts pointer events'), true)
  assert.equal(source.includes("await clickWhenReady(page, createWorkspaceButton)"), true)
  assert.equal(source.includes("await clickWhenReady(page, closeSettingsButton)"), true)
})

test('critical workflow waits for the schema regenerate action to become enabled before clicking', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'e2e/support/criticalWorkflow.js'),
    'utf-8',
  )

  assert.equal(source.includes("const regenerateButton = page.getByRole('button', { name: 'Regenerate', exact: true })"), true)
  assert.equal(source.includes("await expect(regenerateButton).toBeEnabled({ timeout: 30_000 })"), true)
})

test('critical workflow mocks runtime bootstrap and kernel readiness so schema/chat flows do not wait on a real kernel startup', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'e2e/support/criticalWorkflow.js'),
    'utf-8',
  )

  assert.equal(source.includes('mockWorkspaceRuntime = true'), true)
  assert.equal(source.includes("'**/api/v1/workspaces/*/runtime/bootstrap'"), true)
  assert.equal(source.includes("body: JSON.stringify({ reset: true })"), true)
  assert.equal(source.includes("'**/api/v1/workspaces/*/kernel/status'"), true)
  assert.equal(source.includes("body: JSON.stringify({ status: 'ready' })"), true)
})
