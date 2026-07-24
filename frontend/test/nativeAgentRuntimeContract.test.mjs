import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('native agent events and cancellation are scoped to one client request', () => {
  const nativeAnalyze = readFileSync(resolve(process.cwd(), 'src/api/execution.ts'), 'utf-8')

  assert.match(nativeAnalyze, /client_request_id:/)
  assert.match(nativeAnalyze, /crypto\.randomUUID/)
  assert.match(nativeAnalyze, /event\.client_request_id/)
  assert.match(nativeAnalyze, /!== clientRequestId/)
  assert.match(nativeAnalyze, /app\.CancelAgentAnalysis/)
  assert.doesNotMatch(nativeAnalyze, /app\.InterruptWorkspaceKernel/)
})
