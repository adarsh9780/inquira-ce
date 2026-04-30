import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function read(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('account tab exposes theme dropdown wired to app store theme state', () => {
  const source = read('src/components/modals/tabs/AccountTab.vue')

  assert.equal(source.includes("import HeaderDropdown from '../../ui/HeaderDropdown.vue'"), true)
  assert.equal(source.includes("import { useAppStore } from '../../../stores/appStore'"), true)
  assert.equal(source.includes('const appStore = useAppStore()'), true)
  assert.equal(source.includes('const themeOptions = computed(() => {'), true)
  assert.equal(source.includes('label class="mb-1.5 block section-label">Theme</label>'), true)
  assert.equal(source.includes('<HeaderDropdown'), true)
  assert.equal(source.includes(':model-value="appStore.uiTheme"'), true)
  assert.equal(source.includes(':options="themeOptions"'), true)
  assert.equal(source.includes('function selectTheme(themeId) {'), true)
  assert.equal(source.includes('appStore.setUiTheme(themeId)'), true)
})

test('midnight dark theme keeps brand accent while using deep slate surfaces', () => {
  const source = read('src/style.css')

  assert.equal(source.includes(':root[data-theme="midnight"]'), true)
  assert.equal(source.includes('color-scheme: dark;'), true)
  assert.equal(source.includes('--color-base: #111A24;'), true)
  assert.equal(source.includes('--color-surface: #182230;'), true)
  assert.equal(source.includes('--color-sidebar-surface: #0F1721;'), true)
  assert.equal(source.includes('--color-workspace-surface: #141E29;'), true)
  assert.equal(source.includes('--color-accent: #C97443;'), true)
  assert.equal(source.includes('--color-primary-900: #C97443;'), true)
  assert.equal(source.includes('--color-accent-soft: #34261D;'), true)
  assert.equal(source.includes('--color-border: #293748;'), true)
  assert.equal(source.includes('--color-text-main: #E7EDF7;'), true)
  assert.equal(source.includes('--color-panel-elevated: #1C2735;'), true)
  assert.equal(source.includes('--color-selected-surface: #222E3C;'), true)
})

test('theme catalog presents midnight dark with brand-accent preview chip', () => {
  const source = read('src/constants/themes.js')

  assert.equal(source.includes("id: 'midnight'"), true)
  assert.equal(source.includes("label: 'Midnight Dark'"), true)
  assert.equal(source.includes("preview: ['#111A24', '#182230', '#C97443']"), true)
})
