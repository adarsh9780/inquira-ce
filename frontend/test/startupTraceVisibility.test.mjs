import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from './sourceText.mjs'
import { resolve } from 'node:path'

test('startup overlay shows a single status message and elapsed timing hint', () => {
  const appPath = resolve(process.cwd(), 'src/App.vue')
  const source = readFileSync(appPath, 'utf-8')
  const overlay = readFileSync(resolve(process.cwd(), 'src/components/startup/BlockingOperationOverlay.vue'), 'utf-8')

  assert.equal(source.includes('currentStartupProcess'), false)
  assert.equal(overlay.includes('{{ message }}'), true)
  assert.equal(source.includes('startupTimelineEntries'), true)
  assert.equal(source.includes('currentStartupElapsedLabel'), true)
})

test('app records startup stages for workspace progress', () => {
  const appPath = resolve(process.cwd(), 'src/App.vue')
  const source = readFileSync(appPath, 'utf-8')

  assert.equal(source.includes('function recordStartupStage(scope, message)'), true)
  assert.equal(source.includes("recordStartupStage('desktop'"), false)
  assert.equal(source.includes("recordStartupStage('auth'"), false)
  assert.equal(source.includes("recordStartupStage('workspace'"), true)
  assert.equal(source.includes('[STARTUP TRACE]'), true)
})
