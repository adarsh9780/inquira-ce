import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const read = (path) => readFileSync(resolve(process.cwd(), path), 'utf8')

test('Wails theme and font preferences use the SQLite local-state bridge', () => {
  const service = read('src/services/uiPreferencesService.ts')

  assert.equal(service.includes("const UI_PREFERENCES_SCOPE = 'ui-preferences'"), true)
  assert.equal(service.includes('app?.LoadLocalState'), true)
  assert.equal(service.includes('await app.LoadLocalState(UI_PREFERENCES_SCOPE)'), true)
  assert.equal(service.includes('app?.SaveLocalState'), true)
  assert.equal(service.includes('return Boolean(await app.SaveLocalState(UI_PREFERENCES_SCOPE, prefs))'), true)
})
