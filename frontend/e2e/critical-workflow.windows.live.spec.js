import { test } from '@playwright/test'
import { runCriticalWorkflow } from './support/criticalWorkflow.js'
import { isWindows } from './support/platform.js'

test.skip(!isWindows(), 'This native workflow spec only runs on Windows.')
test.skip(!process.env.OPENROUTER_API_KEY, 'This live SSE workflow requires OPENROUTER_API_KEY.')

test('Windows live workflow exercises the real OpenRouter SSE chat stream', async ({ page }) => {
  test.slow()
  await runCriticalWorkflow(page, {
    useLiveChatStream: true,
    expectedResponse: /Carla|1640(?:\.25)?|highest revenue/i,
  })
})
