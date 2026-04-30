import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function read(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('theme catalog exposes supported ids and normalizer helpers', () => {
  const source = read('src/constants/themes.js')

  assert.equal(source.includes("id: 'warm'"), true)
  assert.equal(source.includes("id: 'classiclight'"), true)
  assert.equal(source.includes("id: 'classicdark'"), true)
  assert.equal(source.includes("id: 'evergreen'"), true)
  assert.equal(source.includes("id: 'midnight'"), true)
  assert.equal(source.includes("export const DEFAULT_THEME_ID = 'warm'"), true)
  assert.equal(source.includes('export function normalizeThemeId(value)'), true)
  assert.equal(source.includes('return THEME_IDS.includes(normalized) ? normalized : DEFAULT_THEME_ID'), true)
  assert.equal(source.includes('export function getThemeById(value)'), true)
})

test('app runtime applies html data-theme and persists changes via theme service', () => {
  const source = read('src/App.vue')

  assert.equal(source.includes("import { themeService } from './services/themeService'"), true)
  assert.equal(source.includes("import { normalizeThemeId } from './constants/themes'"), true)
  assert.equal(source.includes('function applyDocumentTheme(themeId) {'), true)
  assert.equal(source.includes("document.documentElement.setAttribute('data-theme', normalized)"), true)
  assert.equal(source.includes('watch('), true)
  assert.equal(source.includes('() => appStore.uiTheme'), true)
  assert.equal(source.includes('void themeService.saveThemePreference(normalized)'), true)
  assert.equal(source.includes('const storedTheme = await themeService.loadThemePreference()'), true)
  assert.equal(source.includes('appStore.setUiTheme(storedTheme, { persist: false })'), true)
})

test('app store snapshot and preference sync include ui_theme', () => {
  const source = read('src/stores/appStore.js')

  assert.equal(source.includes('const uiTheme = ref(DEFAULT_THEME_ID)'), true)
  assert.equal(source.includes('const availableThemes = THEME_OPTIONS.map((theme) => ({ ...theme }))'), true)
  assert.equal(source.includes('ui_theme: uiTheme.value,'), true)
  assert.equal(source.includes('if (typeof ui.ui_theme === \'string\' && ui.ui_theme.trim()) {'), true)
  assert.equal(source.includes('uiTheme.value = normalizeThemeId(ui.ui_theme)'), true)
  assert.equal(source.includes('function setUiTheme(themeId, options = {}) {'), true)
  assert.equal(source.includes('if (options?.persist !== false) {'), true)
})

test('settings modal exposes appearance section and appearance tab updates app theme', () => {
  const modalSource = read('src/components/modals/SettingsModal.vue')
  const tabSource = read('src/components/modals/tabs/AppearanceTab.vue')

  assert.equal(modalSource.includes("import AppearanceTab from './tabs/AppearanceTab.vue'"), true)
  assert.equal(modalSource.includes('Appearance'), true)
  assert.equal(modalSource.includes("@click=\"openLeafSection('appearance')\""), true)
  assert.equal(modalSource.includes("panelClass('appearance')"), true)
  assert.equal(modalSource.includes('<AppearanceTab />'), true)

  assert.equal(tabSource.includes('const activeTheme = computed(() => appStore.uiTheme)'), true)
  assert.equal(tabSource.includes('const themes = computed(() => appStore.availableThemes)'), true)
  assert.equal(tabSource.includes('appStore.setUiTheme(themeId)'), true)
})

test('style sheet declares theme presets and shared token aliases', () => {
  const source = read('src/style.css')

  assert.equal(source.includes(':root[data-theme="warm"]'), true)
  assert.equal(source.includes(':root[data-theme="classiclight"]'), true)
  assert.equal(source.includes(':root[data-theme="classicdark"]'), true)
  assert.equal(source.includes(':root[data-theme="evergreen"]'), true)
  assert.equal(source.includes(':root[data-theme="midnight"]'), true)
  assert.equal(source.includes('--color-text-sub: var(--color-text-muted);'), true)
  assert.equal(source.includes('--color-base-soft: var(--color-surface);'), true)
  assert.equal(source.includes('--color-base-muted:'), true)
  assert.equal(source.includes('--color-border-strong: var(--color-border-hover);'), true)
  assert.equal(source.includes('--color-panel-elevated:'), true)
  assert.equal(source.includes('--color-selected-surface:'), true)
  assert.equal(source.includes('--color-control-surface:'), true)
  assert.equal(source.includes('--color-chart-accent:'), true)
  assert.equal(source.includes('--color-danger: var(--color-error);'), true)
  assert.equal(source.includes('--color-info-bg:'), true)
})

test('appearance tab previews a miniature shell instead of only color swatches', () => {
  const source = read('src/components/modals/tabs/AppearanceTab.vue')

  assert.equal(source.includes('Each preview mirrors the shell hierarchy'), true)
  assert.equal(source.includes('class="mt-3 rounded-xl border p-2"'), true)
  assert.equal(source.includes('class="flex h-20 overflow-hidden rounded-lg border"'), true)
  assert.equal(source.includes("backgroundColor: theme.preview[0]"), true)
})
