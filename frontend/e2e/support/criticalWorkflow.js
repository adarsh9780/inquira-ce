import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { expect } from '@playwright/test'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

export const datasetTableName = 'e2e_sales'
export const datasetFileName = 'e2e_sales.csv'
export const datasetPath = path.resolve(__dirname, '../fixtures', datasetFileName)
const mockAnswerText =
  'The dataset contains three orders. The highest revenue entry belongs to Carla in the West region with revenue of 1640.25 USD.'

function buildSchemaColumns() {
  return [
    {
      name: 'order_id',
      dtype: 'BIGINT',
      description: 'Unique identifier for each order record.',
      aliases: ['order id'],
      samples: [],
    },
    {
      name: 'customer_name',
      dtype: 'VARCHAR',
      description: 'Customer name associated with the order.',
      aliases: ['customer'],
      samples: [],
    },
    {
      name: 'revenue',
      dtype: 'DOUBLE',
      description: 'Revenue amount in USD for the order.',
      aliases: ['sales', 'amount'],
      samples: [],
    },
    {
      name: 'region',
      dtype: 'VARCHAR',
      description: 'Sales region assigned to the order.',
      aliases: ['territory'],
      samples: [],
    },
  ]
}

function buildSeedColumns() {
  return buildSchemaColumns().map((column) => ({
    name: column.name,
    dtype: column.dtype,
    description: '',
    samples: [],
  }))
}

function buildGeneratedSchema(baseSchema = null) {
  return {
    table_name: baseSchema?.table_name || datasetTableName,
    context: baseSchema?.context || 'E2E sales dataset used to validate the critical data workflow.',
    columns: buildSchemaColumns(),
  }
}

function buildSsePayload(events) {
  return `${events
    .map(({ event, data }) => `event: ${event}\ndata: ${JSON.stringify(data)}`)
    .join('\n\n')}\n\n`
}

function isIgnorableRouteError(error) {
  const message = String(error?.message || '')
  return (
    message.includes('Target page, context or browser has been closed') ||
    message.includes('browserContext.close: Test ended.') ||
    message.includes('Test ended.') ||
    message.includes('Route is already handled!')
  )
}

async function fetchRouteResponse(route) {
  try {
    const response = await route.fetch()
    const json = await response.json()
    return { response, json }
  } catch (error) {
    if (isIgnorableRouteError(error)) {
      return null
    }
    throw error
  }
}

async function fulfillRoute(route, payload) {
  try {
    await route.fulfill(payload)
  } catch (error) {
    if (!isIgnorableRouteError(error)) {
      throw error
    }
  }
}

export async function installCriticalWorkflowMocks(page, options = {}) {
  const {
    mockPreferences = true,
    mockSchemaRegenerate = true,
    mockChatStream = true,
    mockWorkspaceRuntime = true,
  } = options
  const state = {
    basePreferences: null,
    lastSchema: null,
    generatedSchema: null,
  }
  const registeredRoutes = []

  const registerRoute = async (url, handler) => {
    registeredRoutes.push({ url, handler })
    await page.route(url, handler)
  }

  const withReadyPreferences = (json) => ({
    ...json,
    api_key_present: true,
    selected_provider_api_key_present: true,
    selected_provider_requires_api_key: true,
    api_key_present_by_provider: {
      ...(json?.api_key_present_by_provider || {}),
      [json?.llm_provider || 'openrouter']: true,
      openrouter: true,
    },
  })

  if (mockPreferences) {
    await registerRoute('**/api/v1/preferences', async (route) => {
      const payload = await fetchRouteResponse(route)
      if (!payload) return
      const { response, json } = payload
      if (route.request().method() === 'GET') {
        state.basePreferences = json
      }

      await fulfillRoute(route, {
        response,
        json: withReadyPreferences(json),
      })
    })

    await registerRoute('**/api/v1/preferences/models/refresh', async (route) => {
      const payload = await fetchRouteResponse(route)
      if (!payload) return
      const { response, json } = payload
      await fulfillRoute(route, {
        response,
        json: withReadyPreferences(json),
      })
    })
  }

  if (mockSchemaRegenerate) {
    await registerRoute('**/api/v1/workspaces/*/datasets/*/schema', async (route) => {
      if (route.request().method() !== 'GET') {
        await route.continue()
        return
      }

      if (state.generatedSchema) {
        await fulfillRoute(route, {
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(state.generatedSchema),
        })
        return
      }

      const payload = await fetchRouteResponse(route)
      if (!payload) return
      const { response, json } = payload
      state.lastSchema = json
      await fulfillRoute(route, {
        response,
        json: state.lastSchema,
      })
    })

    await registerRoute('**/api/v1/workspaces/*/datasets/*/schema/regenerate', async (route) => {
      state.generatedSchema = buildGeneratedSchema(state.lastSchema)

      await fulfillRoute(route, {
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(state.generatedSchema),
      })
    })
  }

  if (mockWorkspaceRuntime) {
    await registerRoute('**/api/v1/workspaces/*/runtime/bootstrap', async (route) => {
      await fulfillRoute(route, {
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ reset: true }),
      })
    })

    await registerRoute('**/api/v1/workspaces/*/kernel/status', async (route) => {
      await fulfillRoute(route, {
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'ready' }),
      })
    })
  }

  if (mockChatStream) {
    await registerRoute('**/api/v1/chat/stream', async (route) => {
      const sseBody = buildSsePayload([
        {
          event: 'status',
          data: {
            stage: 'planning',
            message: 'Inspecting dataset and preparing answer...',
          },
        },
        {
          event: 'final',
          data: {
            is_safe: true,
            code: '',
            current_code: '',
            explanation: mockAnswerText,
            result_explanation: mockAnswerText,
            code_explanation: '',
            metadata: {
              table_names: [datasetTableName],
              source: 'playwright-e2e-mock',
            },
          },
        },
      ])

      await fulfillRoute(route, {
        status: 200,
        headers: {
          'content-type': 'text/event-stream',
          'cache-control': 'no-cache',
          connection: 'keep-alive',
        },
        body: sseBody,
      })
    })
  }

  const cleanup = async () => {
    for (const { url, handler } of registeredRoutes.reverse()) {
      try {
        await page.unroute(url, handler)
      } catch {
        // Ignore shutdown races when the page or browser is already closing.
      }
    }

    try {
      await page.unrouteAll({ behavior: 'ignoreErrors' })
    } catch {
      // Ignore teardown races once the browser starts closing.
    }
  }

  return { state, cleanup }
}

async function waitForAppReady(page, timeout = 90_000) {
  const startupOverlay = page.getByTestId('startup-overlay')
  await expect(startupOverlay).toHaveAttribute('data-active', 'false', { timeout })
}

async function clickWhenReady(page, locator, options = {}) {
  const timeout = Number.isFinite(options.timeout) ? options.timeout : 30_000
  const readinessTimeout = Number.isFinite(options.readinessTimeout) ? options.readinessTimeout : 90_000
  const perAttemptTimeout = Number.isFinite(options.perAttemptTimeout)
    ? options.perAttemptTimeout
    : 5_000
  const retryableFragments = [
    'intercepts pointer events',
    'element is not stable',
    'element was detached from the DOM',
  ]
  let lastError = null

  await waitForAppReady(page, readinessTimeout)

  const deadline = Date.now() + timeout

  while (Date.now() < deadline) {
    await expect(locator).toBeVisible({
      timeout: Math.min(perAttemptTimeout, Math.max(deadline - Date.now(), 1)),
    })

    try {
      await locator.click({ timeout: Math.min(perAttemptTimeout, Math.max(deadline - Date.now(), 1)) })
      return
    } catch (error) {
      lastError = error
      const message = String(error?.message || '')
      const isRetryable = retryableFragments.some((fragment) => message.includes(fragment))
      if (!isRetryable || Date.now() >= deadline) {
        throw error
      }
      await waitForAppReady(page, readinessTimeout)
      await page.waitForTimeout(250)
    }
  }

  if (lastError) {
    throw lastError
  }
}

async function openSidebarForWorkspaceCreation(page) {
  const toggle = page.getByRole('button', { name: 'Open sidebar' })
  await waitForAppReady(page)
  await expect(toggle).toBeVisible({ timeout: 90_000 })

  const preferenceSync = page
    .waitForResponse(
      (response) =>
        response.url().includes('/api/v1/preferences') && response.request().method() === 'PUT',
      { timeout: 5_000 },
    )
    .catch(() => null)

  await clickWhenReady(page, toggle, { timeout: 15_000 })

  const createWorkspaceButton = page.getByTitle('Create Workspace')
  await expect(createWorkspaceButton).toBeVisible({ timeout: 30_000 })
  await preferenceSync
  await waitForAppReady(page)
  await expect(createWorkspaceButton).toBeVisible({ timeout: 30_000 })
  return createWorkspaceButton
}

async function importDatasetFromNativePathBridge(page) {
  await page.evaluate(({ fileName, tableName, columns }) => {
    window.dispatchEvent(
      new CustomEvent('inquira:e2e-select-data-path', {
        detail: {
          fileName,
          tableName,
          rowCount: 3,
          columns,
        },
      }),
    )
  }, {
    fileName: datasetFileName,
    tableName: datasetTableName,
    columns: buildSeedColumns(),
  })
}

export async function setupCriticalWorkspace(page) {
  const workspaceName = `Playwright Workspace ${Date.now()}-${Math.floor(Math.random() * 10_000)}`

  await page.goto('/')
  await waitForAppReady(page)

  const createWorkspaceButton = await openSidebarForWorkspaceCreation(page)
  await clickWhenReady(page, createWorkspaceButton)
  await expect(page.getByRole('dialog')).toBeVisible({ timeout: 10_000 })
  await page.getByLabel('Workspace Name').fill(workspaceName)
  await page.getByRole('dialog').getByRole('button', { name: 'Create Workspace' }).click()

  await expect(page.getByRole('button', { name: workspaceName })).toBeVisible({ timeout: 30_000 })

  await page.getByTitle('Add Dataset').click()
  await expect(page.getByText('Data Configuration')).toBeVisible()

  await importDatasetFromNativePathBridge(page)

  await expect(page.getByText(`Loaded "${datasetFileName}"`)).toBeVisible({ timeout: 60_000 })
  const closeSettingsButton = page.getByLabel('Close settings')
  await expect(closeSettingsButton).toBeEnabled({ timeout: 30_000 })
  await clickWhenReady(page, closeSettingsButton)

  return { workspaceName, tableName: datasetTableName }
}

export async function runCriticalWorkflow(page, options = {}) {
  const {
    useLiveChatStream = false,
    expectedResponse = mockAnswerText,
  } = options
  const { cleanup } = await installCriticalWorkflowMocks(page, {
    mockPreferences: !useLiveChatStream,
    mockSchemaRegenerate: true,
    mockChatStream: !useLiveChatStream,
  })

  try {
    await setupCriticalWorkspace(page)

    await page.getByTitle('Switch to Schema Editor').click()
    await expect(page.getByText('Schema Editor')).toBeVisible()
    await expect(page.getByLabel('Select dataset for schema editor')).toContainText(datasetTableName, { timeout: 30_000 })

    const regenerateButton = page.getByRole('button', { name: 'Regenerate', exact: true })
    await expect(regenerateButton).toBeEnabled({ timeout: 30_000 })
    await clickWhenReady(page, regenerateButton)
    await expect(page.getByText('Generated 4 descriptions')).toBeVisible({ timeout: 30_000 })
    await expect(page.getByText('order_id')).toBeVisible({ timeout: 30_000 })
    await expect(page.getByText('Revenue amount in USD for the order.')).toBeVisible()

    await page.getByTitle('Switch to Workspace').click()
    await page.getByRole('button', { name: 'Chat' }).click()
    await expect(page.getByPlaceholder('How can I help you today?')).toBeVisible()

    const composer = page.getByPlaceholder('How can I help you today?')
    await composer.fill('Which customer has the highest revenue?')
    await composer.press('Enter')

    const responseTimeout = useLiveChatStream ? 120_000 : 30_000
    if (expectedResponse instanceof RegExp) {
      await expect(page.getByText(expectedResponse)).toBeVisible({ timeout: responseTimeout })
    } else {
      await expect(page.getByText(expectedResponse)).toBeVisible({ timeout: responseTimeout })
    }
  } finally {
    await cleanup()
  }
}
