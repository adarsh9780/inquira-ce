import { test } from '@playwright/test'
import { runCriticalWorkflow } from './support/criticalWorkflow.js'
import { isMacOS } from './support/platform.js'

test.skip(!isMacOS(), 'This native workflow spec only runs on macOS.')

test('macOS native workflow covers workspace, dataset, schema, and chat', async ({ page }) => {
  test.slow()
  await runCriticalWorkflow(page)
})
