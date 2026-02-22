import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('settings open actions do not pass click event object as tab', () => {
  const toolbarPath = resolve(process.cwd(), 'src/components/layout/TopToolbar.vue')
  const source = readFileSync(toolbarPath, 'utf-8')

  assert.equal(source.includes('@click="openSettings()"'), true)
  assert.equal(source.includes('@click="openSettings"'), false)
})

test('settings modal normalizes invalid initial tab to api', () => {
  const settingsPath = resolve(process.cwd(), 'src/components/modals/SettingsModal.vue')
  const source = readFileSync(settingsPath, 'utf-8')

  assert.equal(source.includes('function normalizeTab(tab)'), true)
  assert.equal(source.includes("['api', 'data', 'account'].includes(candidate) ? candidate : 'api'"), true)
})
