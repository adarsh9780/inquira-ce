import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('desktop startup waits for the backend health endpoint before auth boot begins', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/App.vue'), 'utf-8')

  assert.equal(source.includes("desktopStartup.message = 'Waiting for backend API...'"), true)
  assert.equal(source.includes('await apiService.waitForBackendReady()'), true)
  assert.equal(source.includes("startupFailure.value = detail"), true)
})
