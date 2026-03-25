import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('apiService exposes authorizedFetch for manual API calls', () => {
  const path = resolve(process.cwd(), 'src/services/apiService.js')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('async function authorizedFetch(input, init = {})'), true)
  assert.equal(source.includes('const response = await authorizedFetch('), true)
  assert.equal(source.includes('subscribeWorkspaceArtifactUsage(workspaceId'), true)
})
