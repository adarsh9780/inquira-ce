import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function read(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('appearance tab owns theme selection wired to app store theme state', () => {
  const source = read('src/components/modals/tabs/AppearanceTab.vue')

  assert.equal(source.includes("import HeaderDropdown from '../../ui/HeaderDropdown.vue'"), true)
  assert.equal(source.includes("import { usePreferencesStore } from '../../../stores/preferencesStore'"), true)
  assert.equal(source.includes('const preferencesStore = usePreferencesStore()'), true)
  assert.equal(source.includes('const activeTheme = computed(() => preferencesStore.uiTheme)'), true)
  assert.equal(source.includes('const themes = computed(() => preferencesStore.availableThemes)'), true)
  assert.equal(source.includes('v-for="theme in themes"'), true)
  assert.equal(source.includes('function selectTheme(themeId) {'), true)
  assert.equal(source.includes('preferencesStore.setUiTheme(themeId)'), true)
})

test('midnight dark theme keeps brand accent while using deep slate surfaces', () => {
  const source = read('src/style.css')

  assert.equal(source.includes(':root[data-theme="midnight"]'), true)
  assert.equal(source.includes('color-scheme: dark;'), true)
  assert.equal(source.includes('--color-base: #101923;'), true)
  assert.equal(source.includes('--color-surface: #16212C;'), true)
  assert.equal(source.includes('--color-sidebar-surface: #0A1119;'), true)
  assert.equal(source.includes('--color-workspace-surface: #0F1722;'), true)
  assert.equal(source.includes('--color-accent: #D98958;'), true)
  assert.equal(source.includes('--color-primary-900: #D98958;'), true)
  assert.equal(source.includes('--color-accent-soft: #33251E;'), true)
  assert.equal(source.includes('--color-border: #273543;'), true)
  assert.equal(source.includes('--color-text-main: #E7EDF5;'), true)
  assert.equal(source.includes('--color-panel-elevated: #1B2835;'), true)
  assert.equal(source.includes('--color-selected-surface: #1D3042;'), true)
  assert.equal(source.includes('--color-on-accent: #101923;'), true)
})

test('theme catalog presents bluehour as the midnight palette with brand-accent preview chip', () => {
  const source = read('src/constants/themes.js')

  assert.equal(source.includes("id: 'midnight'"), true)
  assert.equal(source.includes("label: 'Bluehour'"), true)
  assert.equal(source.includes("preview: ['#101923', '#16212C', '#78A9E6']"), true)
})
