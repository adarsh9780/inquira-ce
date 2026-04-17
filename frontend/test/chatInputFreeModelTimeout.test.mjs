import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat input uses longer auto-cancel timeout for free models', () => {
  const path = resolve(process.cwd(), 'src/components/chat/ChatInput.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('DEFAULT_ANALYZE_CANCEL_TIMEOUT_MS = 300000'), true)
  assert.equal(source.includes('FREE_MODEL_ANALYZE_CANCEL_TIMEOUT_MS = 900000'), true)
  assert.equal(source.includes('DEFAULT_SLOW_REQUEST_WARNING_TIMEOUT_MS = 30000'), true)
  assert.equal(source.includes('function resolveAnalyzeCancelTimeoutMs(modelId)'), true)
  assert.equal(source.includes('function resolveSlowRequestWarningTimeoutMs(seconds)'), true)
  assert.equal(source.includes("normalized.includes('/free')"), true)
  assert.equal(source.includes('const warningAfterMs = resolveSlowRequestWarningTimeoutMs(appStore.slowRequestWarningSeconds)'), true)
  assert.equal(source.includes('}, warningAfterMs)'), true)
  assert.equal(source.includes('const cancelAfterMs = resolveAnalyzeCancelTimeoutMs(appStore.selectedModel)'), true)
  assert.equal(source.includes('}, cancelAfterMs)'), true)
})
