import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { expect } from '@playwright/test'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

export const datasetTableName = 'e2e_sales'
export const datasetFileName = 'e2e_sales.csv'
export const datasetPath = path.resolve(__dirname, '../fixtures', datasetFileName)

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

export async function installCriticalWorkflowMocks(page) {
  const state = {
    basePreferences: null,
    lastSchema: null,
    generatedSchema: null,
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

  await page.route('**/api/v1/preferences', async (route) => {
    const response = await route.fetch()
    const json = await response.json()
    if (route.request().method() === 'GET') {
      state.basePreferences = json
    }

    await route.fulfill({
      response,
      json: withReadyPreferences(json),
    })
  })

  await page.route('**/api/v1/preferences/models/refresh', async (route) => {
    const response = await route.fetch()
    const json = await response.json()
    await route.fulfill({
      response,
      json: withReadyPreferences(json),
    })
  })

  await page.route('**/api/v1/workspaces/*/datasets/*/schema', async (route) => {
    if (route.request().method() !== 'GET') {
      await route.continue()
      return
    }

    if (state.generatedSchema) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(state.generatedSchema),
      })
      return
    }

    const response = await route.fetch()
    state.lastSchema = await response.json()
    await route.fulfill({
      response,
      json: state.lastSchema,
    })
  })

  await page.route('**/api/v1/workspaces/*/datasets/*/schema/regenerate', async (route) => {
    state.generatedSchema = buildGeneratedSchema(state.lastSchema)

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(state.generatedSchema),
    })
  })

  await page.route('**/api/v1/chat/stream', async (route) => {
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
          explanation:
            'The dataset contains three orders. The highest revenue entry belongs to Carla in the West region with revenue of 1640.25 USD.',
          result_explanation:
            'The dataset contains three orders. The highest revenue entry belongs to Carla in the West region with revenue of 1640.25 USD.',
          code_explanation: '',
          metadata: {
            table_names: [datasetTableName],
            source: 'playwright-e2e-mock',
          },
        },
      },
    ])

    await route.fulfill({
      status: 200,
      headers: {
        'content-type': 'text/event-stream',
        'cache-control': 'no-cache',
        connection: 'keep-alive',
      },
      body: sseBody,
    })
  })

  return state
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

export async function runCriticalWorkflow(page) {
  await installCriticalWorkflowMocks(page)

  const workspaceName = `Playwright Workspace ${Date.now()}-${Math.floor(Math.random() * 10_000)}`

  await page.goto('/')

  await expect(page.getByRole('button', { name: 'Open sidebar' })).toBeVisible({ timeout: 90_000 })
  await page.getByRole('button', { name: 'Open sidebar' }).click()

  await page.getByTitle('Create Workspace').click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.getByLabel('Workspace Name').fill(workspaceName)
  await page.getByRole('dialog').getByRole('button', { name: 'Create Workspace' }).click()

  await expect(page.getByRole('button', { name: workspaceName })).toBeVisible({ timeout: 30_000 })

  await page.getByTitle('Add Dataset').click()
  await expect(page.getByText('Data Configuration')).toBeVisible()

  await importDatasetFromNativePathBridge(page)

  await expect(page.getByText(`Loaded "${datasetFileName}"`)).toBeVisible({ timeout: 60_000 })
  await page.getByLabel('Close settings').click()

  await page.getByTitle('Switch to Schema Editor').click()
  await expect(page.getByText('Schema Editor')).toBeVisible()
  await expect(page.getByLabel('Select dataset for schema editor')).toContainText(datasetTableName, { timeout: 30_000 })

  await page.getByRole('button', { name: 'Regenerate' }).click()
  await expect(page.getByText('Generated 4 descriptions')).toBeVisible({ timeout: 30_000 })
  await expect(page.getByText('order_id')).toBeVisible({ timeout: 30_000 })
  await expect(page.getByText('Revenue amount in USD for the order.')).toBeVisible()

  await page.getByTitle('Switch to Workspace').click()
  await page.getByRole('button', { name: 'Chat' }).click()
  await expect(page.getByPlaceholder('How can I help you today?')).toBeVisible()

  const composer = page.getByPlaceholder('How can I help you today?')
  await composer.fill('Which customer has the highest revenue?')
  await composer.press('Enter')

  await expect(
    page.getByText('The dataset contains three orders. The highest revenue entry belongs to Carla in the West region with revenue of 1640.25 USD.'),
  ).toBeVisible({ timeout: 30_000 })
}
