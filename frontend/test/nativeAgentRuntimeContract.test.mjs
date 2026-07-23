import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('native agent events and cancellation are scoped to one client request', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/services/apiService.js'), 'utf-8')
  const start = source.indexOf('async function analyze')
  const end = source.indexOf('\nconst artifactRowsInFlight', start)
  const nativeAnalyze = source.slice(start, end)

  assert.match(nativeAnalyze, /client_request_id:/)
  assert.match(nativeAnalyze, /crypto\.randomUUID/)
  assert.match(nativeAnalyze, /event\?\.client_request_id/)
  assert.match(nativeAnalyze, /!== clientRequestId/)
  assert.match(nativeAnalyze, /app\.CancelAgentAnalysis/)
  assert.doesNotMatch(nativeAnalyze, /app\.InterruptWorkspaceKernel/)
})
