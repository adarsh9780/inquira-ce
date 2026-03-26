import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('desktop startup screen uses a fixed-height scrollable progress panel', () => {
  const appPath = resolve(process.cwd(), 'src/App.vue')
  const source = readFileSync(appPath, 'utf-8')

  assert.equal(source.includes('desktop-startup-progress-scroll'), true)
  assert.equal(source.includes('startup-progress-scroll'), true)
  assert.equal(source.includes('h-[34rem]'), true)
  assert.equal(source.includes('startup-brand-logo'), true)
})

test('startup progress deduplicates repeated stage messages', () => {
  const appPath = resolve(process.cwd(), 'src/App.vue')
  const source = readFileSync(appPath, 'utf-8')

  assert.equal(source.includes('function recordDesktopStartupStage(message)'), true)
  assert.equal(source.includes('function normalizeStartupMessage(message)'), true)
  assert.equal(source.includes('current?.message === rendered'), true)
  assert.equal(source.includes('current?.scope === scope && current?.canonicalMessage === canonicalMessage'), true)
})
