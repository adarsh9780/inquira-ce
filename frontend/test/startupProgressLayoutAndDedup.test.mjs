import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from './sourceText.mjs'
import { resolve } from 'node:path'

test('desktop startup screen uses minimal centered layout', () => {
  const appPath = resolve(process.cwd(), 'src/App.vue')
  const source = readFileSync(appPath, 'utf-8')

  // Startup progress scroll classes still exist for scroll behavior
  assert.equal(source.includes('startup-progress-scroll'), true)
  assert.equal(source.includes('desktop-startup-progress-scroll'), true)
  // Startup brand logo animation still exists
  assert.equal(source.includes('startup-brand-logo'), true)
  // The fixed height h-[34rem] was removed in the minimal redesign
  assert.equal(source.includes('h-[34rem]'), false)
})

test('startup progress deduplicates repeated stage messages', () => {
  const appPath = resolve(process.cwd(), 'src/App.vue')
  const source = readFileSync(appPath, 'utf-8')

  assert.equal(source.includes('function recordDesktopStartupStage(message)'), true)
  assert.equal(source.includes('function normalizeStartupMessage(message)'), true)
  assert.equal(source.includes('current?.message === rendered'), true)
  assert.equal(source.includes('current?.scope === scope && current?.canonicalMessage === canonicalMessage'), true)
})

test('desktop startup polls the native Go startup state for live progress', () => {
  const appPath = resolve(process.cwd(), 'src/App.vue')
  const source = readFileSync(appPath, 'utf-8')

  assert.equal(source.includes('async function readDesktopStartupState()'), true)
  assert.equal(source.includes('if (app?.GetStartupState)'), true)
  assert.equal(source.includes('const state = await readDesktopStartupState()'), true)
})
