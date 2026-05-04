import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function read(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('appearance tab exposes app and code font selectors wired to app store state', () => {
  const source = read('src/components/modals/tabs/AppearanceTab.vue')

  assert.equal(source.includes('label class="mb-2 block text-sm font-semibold text-[var(--color-text-main)]">App Font</label>'), true)
  assert.equal(source.includes('label class="mb-2 block text-sm font-semibold text-[var(--color-text-main)]">Code Editor Font</label>'), true)
  assert.equal(source.includes("import HeaderDropdown from '../../ui/HeaderDropdown.vue'"), true)
  assert.equal(source.includes(':model-value="activeFont"'), true)
  assert.equal(source.includes(':options="appFontOptions"'), true)
  assert.equal(source.includes('@update:model-value="selectFont"'), true)
  assert.equal(source.includes('appStore.setUiFont(fontId)'), true)
  assert.equal(source.includes(':model-value="activeCodeFont"'), true)
  assert.equal(source.includes(':options="codeFontOptions"'), true)
  assert.equal(source.includes('@update:model-value="selectCodeFont"'), true)
  assert.equal(source.includes('appStore.setUiCodeFont(fontId)'), true)
})

test('app shell applies and persists font preference through font service', () => {
  const source = read('src/App.vue')

  assert.equal(source.includes("import { fontService } from './services/fontService'"), true)
  assert.equal(source.includes("import { normalizeAppFontId, normalizeCodeFontId } from './constants/fonts'"), true)
  assert.equal(source.includes("document.documentElement.setAttribute('data-font', normalized)"), true)
  assert.equal(source.includes("document.documentElement.setAttribute('data-code-font', normalized)"), true)
  assert.equal(source.includes('() => appStore.uiFont'), true)
  assert.equal(source.includes('() => appStore.uiCodeFont'), true)
  assert.equal(source.includes('void fontService.saveAppFontPreference(normalized)'), true)
  assert.equal(source.includes('void fontService.saveCodeFontPreference(normalized)'), true)
  assert.equal(source.includes('appStore.setUiFont(storedFont, { persist: false })'), true)
  assert.equal(source.includes('appStore.setUiCodeFont(storedCodeFont, { persist: false })'), true)
})

test('style and store include app and code font catalogs', () => {
  const styleSource = read('src/style.css')
  const storeSource = read('src/stores/appStore.js')
  const fontsSource = read('src/constants/fonts.js')

  assert.equal(styleSource.includes('family=Ubuntu:wght@400;500;700'), true)
  assert.equal(styleSource.includes('family=Inter:wght@400;500;600;700'), true)
  assert.equal(styleSource.includes('family=Source+Sans+3:wght@400;600;700'), true)
  assert.equal(styleSource.includes('family=IBM+Plex+Sans:wght@400;500;600;700'), true)
  assert.equal(styleSource.includes('family=Fira+Code:wght@400;500;700'), true)
  assert.equal(styleSource.includes('family=Source+Code+Pro:wght@400;600;700'), true)
  assert.equal(styleSource.includes('family=IBM+Plex+Mono:wght@400;500;700'), true)
  assert.equal(styleSource.includes('family=Roboto+Mono:wght@400;500;700'), true)
  assert.equal(styleSource.includes(':root[data-font="ubuntu"]'), true)
  assert.equal(styleSource.includes(':root[data-code-font="jetbrains-mono"]'), true)
  assert.equal(styleSource.includes(':root[data-code-font="fira-code"]'), true)
  assert.equal(fontsSource.includes("id: 'ubuntu'"), true)
  assert.equal(fontsSource.includes("id: 'jetbrains-mono'"), true)
  assert.equal(storeSource.includes('const uiFont = ref(DEFAULT_APP_FONT_ID)'), true)
  assert.equal(storeSource.includes('const uiCodeFont = ref(DEFAULT_CODE_FONT_ID)'), true)
  assert.equal(storeSource.includes('function setUiFont(fontId, options = {}) {'), true)
  assert.equal(storeSource.includes('function setUiCodeFont(fontId, options = {}) {'), true)
})
