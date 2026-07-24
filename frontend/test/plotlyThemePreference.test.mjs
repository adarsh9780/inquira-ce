import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app store reads plotly theme mode from v1 preferences payload', () => {
  const path = resolve(process.cwd(), 'src/stores/appCoordinatorStore.js')
  const source = `${readFileSync(resolve(process.cwd(), 'src/stores/preferencesStore.ts'), 'utf-8')}\n${readFileSync(path, 'utf-8')}`

  assert.equal(source.includes('const plotlyThemeMode = ref(\'soft\')'), true)
  assert.equal(source.includes('prefs?.plotly_theme_mode'), true)
  assert.equal(source.includes('plotlyThemeMode.value = normalizedPlotlyThemeMode === \'hard\' ? \'hard\' : \'soft\''), true)
})

test('figure tab resolves chart theme mode from app store setting', () => {
  const path = resolve(process.cwd(), 'src/components/analysis/FigureTab.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('appStore.plotlyThemeMode'), true)
  assert.equal(source.includes('layout?.meta?.inquira_theme_mode'), false)
})
