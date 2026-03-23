import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('startup overlay shows current process and recent timing entries', () => {
  const appPath = resolve(process.cwd(), 'src/App.vue')
  const source = readFileSync(appPath, 'utf-8')

  assert.equal(source.includes('Current process'), true)
  assert.equal(source.includes('currentStartupProcess'), true)
  assert.equal(source.includes('startupTimelineEntries'), true)
  assert.equal(source.includes('currentStartupElapsedLabel'), true)
})

test('app records startup stages for desktop, auth, workspace, and runtime progress', () => {
  const appPath = resolve(process.cwd(), 'src/App.vue')
  const source = readFileSync(appPath, 'utf-8')

  assert.equal(source.includes('function recordStartupStage(scope, message)'), true)
  assert.equal(source.includes("recordStartupStage('desktop'"), true)
  assert.equal(source.includes("recordStartupStage('auth'"), true)
  assert.equal(source.includes("recordStartupStage('workspace'"), true)
  assert.equal(source.includes("recordStartupStage('runtime'"), true)
  assert.equal(source.includes('[STARTUP TRACE]'), true)
})
