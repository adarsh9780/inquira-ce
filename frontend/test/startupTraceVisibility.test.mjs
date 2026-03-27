import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('startup overlay shows a single status message and elapsed timing hint', () => {
  const appPath = resolve(process.cwd(), 'src/App.vue')
  const source = readFileSync(appPath, 'utf-8')

  assert.equal(source.includes('currentStartupProcess'), false)
  assert.equal(source.includes('{{ startupOverlayMessage }}'), true)
  assert.equal(source.includes('startupTimelineEntries'), true)
  assert.equal(source.includes('currentStartupElapsedLabel'), true)
})

test('app records startup stages for authenticated workspace and runtime progress', () => {
  const appPath = resolve(process.cwd(), 'src/App.vue')
  const source = readFileSync(appPath, 'utf-8')

  assert.equal(source.includes('function recordStartupStage(scope, message)'), true)
  assert.equal(source.includes("recordStartupStage('desktop'"), false)
  assert.equal(source.includes("recordStartupStage('auth'"), false)
  assert.equal(source.includes("recordStartupStage('workspace'"), true)
  assert.equal(source.includes("recordStartupStage('runtime'"), true)
  assert.equal(source.includes('[STARTUP TRACE]'), true)
})
