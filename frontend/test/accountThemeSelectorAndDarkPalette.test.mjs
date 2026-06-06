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
  assert.equal(source.includes('--color-base: #101821;'), true)
  assert.equal(source.includes('--color-surface: #182431;'), true)
  assert.equal(source.includes('--color-sidebar-surface: #0D151E;'), true)
  assert.equal(source.includes('--color-workspace-surface: #121C27;'), true)
  assert.equal(source.includes('--color-accent: #D18455;'), true)
  assert.equal(source.includes('--color-primary-900: #D18455;'), true)
  assert.equal(source.includes('--color-accent-soft: #38291F;'), true)
  assert.equal(source.includes('--color-border: #2D3C4D;'), true)
  assert.equal(source.includes('--color-text-main: #F1F5FA;'), true)
  assert.equal(source.includes('--color-panel-elevated: #1C2937;'), true)
  assert.equal(source.includes('--color-selected-surface: #243345;'), true)
  assert.equal(source.includes('--color-on-accent: #101821;'), true)
})

test('theme catalog presents bluehour as the midnight palette with brand-accent preview chip', () => {
  const source = read('src/constants/themes.js')

  assert.equal(source.includes("id: 'midnight'"), true)
  assert.equal(source.includes("label: 'Bluehour'"), true)
  assert.equal(source.includes("preview: ['#101821', '#182431', '#D18455']"), true)
})
