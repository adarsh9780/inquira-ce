import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app startup uses a shared backend-ready path for both health polling and tauri ready events', () => {
  const appPath = resolve(process.cwd(), 'src/App.vue')
  const source = readFileSync(appPath, 'utf-8')

  assert.equal(source.includes('function markBackendReady()'), true)
  assert.equal(source.includes("if (event.payload === 'ready') {\n          markBackendReady()"), true)
  assert.equal(source.includes('await apiService.waitForBackendReady()'), true)
  assert.equal(source.includes('markBackendReady()'), true)
})

test('app startup keeps probing backend health after the initial timeout so the overlay can recover', () => {
  const appPath = resolve(process.cwd(), 'src/App.vue')
  const source = readFileSync(appPath, 'utf-8')

  assert.equal(source.includes('async function recoverBackendReadiness()'), true)
  assert.equal(source.includes('await apiService.waitForBackendReady(2000)'), true)
  assert.equal(source.includes("backendStatus.message = 'Backend is taking longer than expected to start.'"), true)
  assert.equal(source.includes('void recoverBackendReadiness()'), true)
})
