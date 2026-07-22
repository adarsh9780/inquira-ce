import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { uiPreferencesService } from '../src/services/uiPreferencesService.js'

const read = (path) => readFileSync(resolve(process.cwd(), path), 'utf8')

test('Wails theme and font preferences use the SQLite local-state bridge before Tauri or localStorage', () => {
  const service = read('src/services/uiPreferencesService.js')
  const getPreferences = service.slice(service.indexOf('async getPreferences()'), service.indexOf('async savePreferences(prefs)'))

  assert.equal(service.includes("const UI_PREFERENCES_SCOPE = 'ui-preferences'"), true)
  assert.equal(service.includes('app?.LoadLocalState'), true)
  assert.equal(service.includes('await app.LoadLocalState(UI_PREFERENCES_SCOPE)'), true)
  assert.equal(service.includes('app?.SaveLocalState'), true)
  assert.equal(service.includes('return Boolean(await app.SaveLocalState(UI_PREFERENCES_SCOPE, prefs))'), true)
  assert.equal(getPreferences.indexOf('app?.LoadLocalState') < getPreferences.indexOf('if (!isTauriRuntime())'), true)
})

test('first native load migrates valid legacy localStorage preferences without losing startup styling', () => {
  const service = read('src/services/uiPreferencesService.js')

  assert.equal(service.includes('function loadLegacyBrowserPreferences()'), true)
  assert.equal(service.includes("localStorage.getItem('ui_preferences')"), true)
  assert.equal(service.includes('await app.SaveLocalState(UI_PREFERENCES_SCOPE, legacyPreferences)'), true)
  assert.equal(service.includes("console.warn('Failed to load UI preferences through Wails:'"), true)
  assert.equal(service.includes("console.warn('Failed to save UI preferences through Wails:'"), true)
})

test('native preference bridge migrates once and round-trips saves', async (t) => {
  const calls = []
  const removedKeys = []
  globalThis.localStorage = {
    getItem: (key) => key === 'ui_preferences' ? JSON.stringify({ ui_theme: 'midnight', ui_font: 'inter' }) : null,
    setItem: () => { throw new Error('native saves must not use localStorage') },
    removeItem: (key) => removedKeys.push(key),
  }
  globalThis.window = {
    go: { main: { App: {
      LoadLocalState: async (scope) => { calls.push(['load', scope]); return null },
      SaveLocalState: async (scope, payload) => { calls.push(['save', scope, payload]); return true },
    } } },
  }
  t.after(() => {
    delete globalThis.window
    delete globalThis.localStorage
  })

  const loaded = await uiPreferencesService.getPreferences()
  assert.deepEqual(loaded, { ui_theme: 'midnight', ui_font: 'inter' })
  assert.deepEqual(calls, [
    ['load', 'ui-preferences'],
    ['save', 'ui-preferences', { ui_theme: 'midnight', ui_font: 'inter' }],
  ])
  assert.deepEqual(removedKeys, ['ui_preferences'])

  calls.length = 0
  const saved = await uiPreferencesService.savePreferences({ ui_code_font: 'jetbrains-mono' })
  assert.equal(saved, true)
  assert.deepEqual(calls, [['save', 'ui-preferences', { ui_code_font: 'jetbrains-mono' }]])
})

test('native preference bridge keeps startup defaults available when SQLite is temporarily unavailable', async (t) => {
  const warnings = []
  const originalWarn = console.warn
  console.warn = (...args) => warnings.push(args)
  globalThis.localStorage = {
    getItem: () => JSON.stringify({ ui_theme: 'light' }),
    setItem: () => {},
  }
  globalThis.window = {
    go: { main: { App: {
      LoadLocalState: async () => { throw new Error('database busy') },
      SaveLocalState: async () => { throw new Error('database busy') },
    } } },
  }
  t.after(() => {
    console.warn = originalWarn
    delete globalThis.window
    delete globalThis.localStorage
  })

  assert.deepEqual(await uiPreferencesService.getPreferences(), { ui_theme: 'light' })
  assert.equal(await uiPreferencesService.savePreferences({ ui_theme: 'dark' }), false)
  assert.equal(warnings.length, 2)
})
