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

test('critical workflow opens current workspace settings flow before creating a workspace', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'e2e/support/criticalWorkflow.js'),
    'utf-8',
  )

  assert.equal(source.includes("const workspaceSettingsButton = page.getByTitle('Workspace settings')"), true)
  assert.equal(source.includes("const expandSidebarButton = page.getByTitle('Expand sidebar')"), true)
  assert.equal(source.includes("await clickWhenReady(page, workspaceSettingsButton, { timeout: 15_000 })"), true)
  assert.equal(source.includes("page.getByRole('button', { name: '+ New' })"), true)
  assert.equal(source.includes("page.getByPlaceholder('New workspace name')"), true)
  assert.equal(source.includes("const addDatasetButton = page.getByRole('button', { name: 'Add dataset' })"), true)
  assert.equal(source.includes('const activateWorkspaceButton = page.getByRole'), true)
  assert.equal(source.includes('await activateWorkspaceButton.click({ timeout: 3_000 })'), true)
  assert.equal(source.includes("page.getByRole('dialog').getByRole('button', { name: 'Create Workspace' })"), false)
  assert.equal(source.includes("page.getByRole('button', { name: 'Open sidebar' })"), false)
  assert.equal(source.includes("response.url().includes('/api/v1/preferences')"), true)
  assert.equal(source.includes("response.request().method() === 'PUT'"), true)
  assert.equal(source.includes('await preferenceSync'), true)
  assert.equal(source.includes('await createWorkspaceFromSettings(page, workspaceName)'), true)
})

test('critical workflow mocks current async dataset ingestion flow', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'e2e/support/criticalWorkflow.js'),
    'utf-8',
  )

  assert.equal(source.includes('mockDatasetIngestion = true'), true)
  assert.equal(source.includes("'**/api/v1/workspaces/*/datasets/batch'"), true)
  assert.equal(source.includes("'**/api/v1/workspaces/*/datasets/ingestions/*'"), true)
  assert.equal(source.includes('const datasetListRoute = /\\/api\\/v1\\/workspaces\\/[^/]+\\/datasets(?:\\?.*)?$/'), true)
  assert.equal(source.includes('state.lastSchema = buildGeneratedSchema(state.lastSchema)'), true)
  assert.equal(source.includes("new CustomEvent('inquira:e2e-select-data-path'"), true)
  assert.equal(source.includes("await expect(page.getByText(datasetFileName, { exact: true }))"), true)
})

test('critical workflow mocks conversation lifecycle around chat stream', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'e2e/support/criticalWorkflow.js'),
    'utf-8',
  )

  assert.equal(source.includes('const conversationsRoute = /\\/api\\/v1\\/workspaces\\/[^/]+\\/conversations(?:\\?.*)?$/'), true)
  assert.equal(source.includes('const turnsRoute = /\\/api\\/v1\\/conversations\\/[^/]+\\/turns(?:\\?.*)?$/'), true)
  assert.equal(source.includes("'**/api/v1/conversations/*/turns/*/relations'"), true)
  assert.equal(source.includes("'**/api/v1/conversations/*/turn-tree**'"), true)
  assert.equal(source.includes("'**/api/v1/workspaces/*/turn-tree'"), true)
  assert.equal(source.includes('conversation_id: conversationId'), true)
  assert.equal(source.includes('turn_id: turnId'), true)
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
  assert.equal(source.includes("await clickWhenReady(page, page.getByRole('button', { name: '+ New' }))"), true)
  assert.equal(source.includes("await clickWhenReady(page, closeSettingsButton)"), true)
})

test('critical workflow waits for the schema regenerate action to become enabled before clicking', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'e2e/support/criticalWorkflow.js'),
    'utf-8',
  )

  assert.equal(source.includes('await clickWhenReady(page, page.getByTitle(/Schema editor/i))'), true)
  assert.equal(source.includes("await expect(page.getByText('Workspace Schema')).toBeVisible()"), true)
  assert.equal(source.includes("page.getByRole('heading', { name: datasetTableName, exact: true })"), true)
  assert.equal(source.includes("page.getByTitle('Switch to Schema Editor')"), false)
  assert.equal(source.includes("page.getByTitle('Switch to Workspace')"), false)
  assert.equal(source.includes("await clickWhenReady(page, page.getByTitle(workspaceName).first())"), true)
  assert.equal(source.includes("page.getByRole('button', { name: 'Chat', exact: true })"), true)
  assert.equal(source.includes("const regenerateButton = page.getByRole('button', { name: 'Regenerate', exact: true })"), true)
  assert.equal(source.includes("await expect(regenerateButton).toBeEnabled({ timeout: 30_000 })"), true)
})

test('critical workflow mocks runtime bootstrap and runtime readiness so schema/chat flows do not wait on a real runtime startup', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'e2e/support/criticalWorkflow.js'),
    'utf-8',
  )

  assert.equal(source.includes('mockWorkspaceRuntime = true'), true)
  assert.equal(source.includes("'**/api/v1/workspaces/*/runtime/bootstrap'"), true)
  assert.equal(source.includes("body: JSON.stringify({ reset: true })"), true)
  assert.equal(source.includes("'**/api/v1/workspaces/*/runtime/status'"), true)
  assert.equal(source.includes("body: JSON.stringify({ status: 'ready' })"), true)
})
