import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('status bar stops kernel/artifact polling when unauthorized responses occur', () => {
  const path = resolve(process.cwd(), 'src/components/layout/StatusBar.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('function isUnauthorizedError(error)'), true)
  assert.equal(source.includes('async function handleUnauthorizedPollingError()'), true)
  assert.equal(source.includes('stopKernelStatusPolling()'), true)
  assert.equal(source.includes('stopArtifactUsagePolling()'), true)
  assert.equal(source.includes("appStore.setRuntimeError('Session expired. Please sign in again.')"), true)
  assert.equal(source.includes('if (isUnauthorizedError(error)) {'), true)
  assert.equal(source.includes('if (!authStore.isAuthenticated) return'), true)
  assert.equal(source.includes('() => authStore.isAuthenticated'), true)
})
