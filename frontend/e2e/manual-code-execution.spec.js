import { test, expect } from '@playwright/test'
import { installCriticalWorkflowMocks, setupCriticalWorkspace } from './support/criticalWorkflow.js'

function selectAllShortcut() {
  return process.platform === 'darwin' ? 'Meta+A' : 'Control+A'
}

test('manual code edit runs and shows result output', async ({ page }) => {
  const { cleanup } = await installCriticalWorkflowMocks(page, {
    mockPreferences: true,
    mockSchemaRegenerate: false,
    mockChatStream: false,
  })

  let executionRequest = null
  await page.route('**/api/v1/workspaces/*/execute', async (route) => {
    executionRequest = route.request().postDataJSON()
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        stdout: 'top_customer=Carla',
        stderr: '',
        has_stdout: true,
        has_stderr: false,
        error: '',
        result: null,
        result_type: 'none',
        result_kind: 'none',
        result_name: '',
        run_id: 'pw-manual-run',
        artifacts: [],
        variables: {
          figures: {
            stale_fig: { data: [{ type: 'bar', y: [1] }], layout: { title: 'stale-chart' } },
          },
        },
      }),
    })
  })

  try {
    await setupCriticalWorkspace(page)

    await expect(page.getByRole('tab', { name: 'Code', exact: true })).toBeVisible()
    await page.getByRole('tab', { name: 'Code', exact: true }).click()

    const editor = page.locator('.cm-content').first()
    await expect(editor).toBeVisible({ timeout: 30_000 })
    await editor.click()
    await page.keyboard.press(selectAllShortcut())
    await page.keyboard.type(
      [
        'top_customer = conn.sql("SELECT customer_name FROM e2e_sales ORDER BY revenue DESC LIMIT 1").fetchone()[0]',
        'print(f"top_customer={top_customer}")',
      ].join('\n'),
    )

    await page.getByTitle('Run Code (R)').click()
    await expect(page.getByText('top_customer=Carla')).toBeVisible({ timeout: 30_000 })
    const categoryButton = page.getByRole('button', { name: 'Select result category' })
    await expect(categoryButton).toContainText('Runs')
    await expect(categoryButton.locator('[data-header-dropdown-icon]')).toHaveCount(1)
    await expect(page.locator('[data-runs-feed] [data-user-run]')).toHaveCount(1)
    await expect(page.locator('[data-runs-feed] [data-execution-code]')).toContainText('top_customer = conn.sql')
    await expect(page.locator('[data-runs-feed] [data-run-chart]')).toHaveCount(0)
    expect(executionRequest?.result_mode).toBe('jupyter')

    await page.getByRole('button', { name: 'Delete run' }).click()
    await expect(page.locator('[data-runs-feed] [data-user-run]')).toHaveCount(0)
    await expect(page.getByText('No manual runs yet')).toBeVisible()
  } finally {
    await cleanup()
  }
})

test('manual dataframe run stays in one block and can be promoted to Tables', async ({ page }) => {
  const { cleanup } = await installCriticalWorkflowMocks(page, {
    mockPreferences: true,
    mockSchemaRegenerate: false,
    mockChatStream: false,
  })

  await page.route('**/api/v1/workspaces/*/execute', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        stdout: 'rows=2',
        stderr: '',
        has_stdout: true,
        has_stderr: false,
        error: '',
        result: {
          columns: ['customer_name', 'revenue'],
          data: [
            ['Carla', 2400],
            ['Dev', 1800],
          ],
          row_count: 2,
        },
        result_type: 'DataFrame',
        result_kind: 'dataframe',
        result_name: 'result',
        run_id: 'pw-manual-table-run',
        artifacts: [],
        variables: {},
      }),
    })
  })

  try {
    await setupCriticalWorkspace(page)
    await page.getByRole('tab', { name: 'Code', exact: true }).click()

    const editor = page.locator('.cm-content').first()
    await expect(editor).toBeVisible({ timeout: 30_000 })
    await editor.click()
    await page.keyboard.press(selectAllShortcut())
    await page.keyboard.type('result = conn.sql("SELECT customer_name, revenue FROM e2e_sales LIMIT 2").df()\nresult')

    await page.getByTitle('Run Code (R)').click()

    const categoryButton = page.getByRole('button', { name: 'Select result category' })
    await expect(categoryButton).toContainText('Runs')
    await expect(categoryButton.locator('[data-header-dropdown-icon]')).toHaveCount(1)
    await expect(page.locator('[data-runs-feed] [data-user-run]')).toHaveCount(1)
    await expect(page.locator('[data-runs-feed] [data-run-table]')).toBeVisible({ timeout: 30_000 })
    await expect(page.locator('[data-runs-feed]').getByText('Carla', { exact: true })).toBeVisible()
    await expect(page.getByText('rows=2', { exact: true })).toBeVisible()
    await expect(page.locator('[data-runs-feed] [data-execution-code]')).toContainText('result = conn.sql')
    await expect(page.locator('[data-inquira-data-grid]')).toHaveCount(0)
    await page.getByRole('button', { name: /open in tables/i }).click()
    await expect(categoryButton).toContainText('Tables')
    await expect(page.getByRole('grid', { name: 'Table data' })).toBeVisible({ timeout: 30_000 })
    await expect(page.getByRole('button', { name: 'Select table' })).toContainText('User revision')
    await expect(page.locator('[data-inquira-data-grid]')).toHaveCount(1)
  } finally {
    await cleanup()
  }
})

test('large manual output can open in a focused full-output view', async ({ page }) => {
  const { cleanup } = await installCriticalWorkflowMocks(page, {
    mockPreferences: true,
    mockSchemaRegenerate: false,
    mockChatStream: false,
  })
  const largeOutput = `${'x'.repeat(4_500)}END`

  await page.route('**/api/v1/workspaces/*/execute', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        stdout: largeOutput,
        stderr: '',
        has_stdout: true,
        has_stderr: false,
        error: '',
        result: null,
        result_type: 'none',
        result_kind: 'none',
        result_name: '',
        run_id: 'pw-large-run',
        artifacts: [],
        variables: {},
      }),
    })
  })

  try {
    await setupCriticalWorkspace(page)
    await page.getByRole('tab', { name: 'Code', exact: true }).click()

    const editor = page.locator('.cm-content').first()
    await expect(editor).toBeVisible({ timeout: 30_000 })
    await editor.click()
    await page.keyboard.press(selectAllShortcut())
    await page.keyboard.type("print('large output')")
    await page.getByTitle('Run Code (R)').click()

    const stdout = page.locator('[data-runs-feed] [data-execution-stdout]')
    await expect(stdout).toBeVisible({ timeout: 30_000 })
    await expect(stdout).not.toContainText('END')
    await page.getByRole('button', { name: 'Open full output' }).first().click()
    await expect(page.getByText('Full output', { exact: true })).toBeVisible()
    await expect(stdout).toContainText('END')
    await page.getByRole('button', { name: 'Preview output' }).click()
    await expect(page.getByRole('button', { name: 'Open full output' }).first()).toBeVisible()
  } finally {
    await cleanup()
  }
})

test('manual run navigator defaults to latest and can move through history', async ({ page }) => {
  const { cleanup } = await installCriticalWorkflowMocks(page, {
    mockPreferences: true,
    mockSchemaRegenerate: false,
    mockChatStream: false,
  })
  let executionCount = 0

  await page.route('**/api/v1/workspaces/*/execute', async (route) => {
    executionCount += 1
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        stdout: `output-${executionCount}`,
        stderr: '',
        has_stdout: true,
        has_stderr: false,
        error: '',
        result: null,
        result_type: 'none',
        result_kind: 'none',
        result_name: '',
        run_id: `pw-navigator-run-${executionCount}`,
        artifacts: [],
        variables: {},
      }),
    })
  })

  try {
    await setupCriticalWorkspace(page)
    await page.getByRole('tab', { name: 'Code', exact: true }).click()

    const editor = page.locator('.cm-content').first()
    await expect(editor).toBeVisible({ timeout: 30_000 })
    await editor.click()
    await page.keyboard.press(selectAllShortcut())
    await page.keyboard.type("print('navigator')")

    await page.getByTitle('Run Code (R)').click()
    await expect(page.getByText('output-1', { exact: true })).toBeVisible({ timeout: 30_000 })
    await page.getByTitle('Run Code (R)').click()
    await expect(page.getByText('output-2', { exact: true })).toBeVisible({ timeout: 30_000 })

    const runSelector = page.getByRole('button', { name: 'Select run from history' })
    await expect(runSelector).toContainText('Run 2 of 2')
    await expect(page.locator('[data-runs-feed] [data-user-run]')).toHaveCount(1)
    await expect(page.getByText('output-1', { exact: true })).toHaveCount(0)

    await page.getByRole('button', { name: 'Previous run' }).click()
    await expect(runSelector).toContainText('Run 1 of 2')
    await expect(page.getByText('output-1', { exact: true })).toBeVisible()
    await page.getByRole('button', { name: 'Next run' }).click()
    await expect(page.getByText('output-2', { exact: true })).toBeVisible()

    await runSelector.click()
    await page.getByRole('option', { name: /Run 1 · Text/ }).click()
    await expect(page.getByText('output-1', { exact: true })).toBeVisible()
    await page.getByRole('button', { name: 'Delete run' }).click()
    await expect(runSelector).toContainText('Run 1 of 1')
    await expect(page.getByText('output-2', { exact: true })).toBeVisible()
  } finally {
    await cleanup()
  }
})
