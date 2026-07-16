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

  await page.route('**/api/v1/workspaces/*/execute', async (route) => {
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
        variables: {},
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
    await page.getByRole('button', { name: /current table/i }).click()
    await expect(categoryButton).toContainText('Tables')
    await expect(page.getByRole('grid', { name: 'Table data' })).toBeVisible({ timeout: 30_000 })
    await expect(page.getByRole('button', { name: 'Select table' })).toContainText('User revision')
    await expect(page.locator('[data-inquira-data-grid]')).toHaveCount(1)
  } finally {
    await cleanup()
  }
})
