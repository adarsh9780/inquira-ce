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

    await expect(page.getByRole('button', { name: 'Code' })).toBeVisible()

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
  } finally {
    await cleanup()
  }
})
