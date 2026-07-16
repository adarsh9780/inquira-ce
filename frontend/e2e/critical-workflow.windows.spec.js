import { test } from '@playwright/test'
import { runCriticalWorkflow } from './support/criticalWorkflow.js'
import { isWindows } from './support/platform.js'

test.skip(!isWindows(), 'This native workflow spec only runs on Windows.')

test('Windows native workflow covers workspace, dataset, schema, and chat', async ({ page }) => {
  test.slow()
  await runCriticalWorkflow(page)
})
