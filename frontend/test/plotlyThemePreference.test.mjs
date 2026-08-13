import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app store does not expose a remote Plotly theme preference', () => {
  const path = resolve(process.cwd(), 'src/stores/preferencesStore.ts')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('plotlyThemeMode'), false)
  assert.equal(source.includes('prefs?.plotly_theme_mode'), false)
})

test('figure tab consistently applies the enforced Inquira token theme', () => {
  const path = resolve(process.cwd(), 'src/components/analysis/FigureTab.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('appStore.plotlyThemeMode'), false)
  assert.equal(source.includes('const themeMode = PLOTLY_THEME_MODE.HARD'), true)
  assert.equal(source.includes('layout?.meta?.inquira_theme_mode'), false)
})
