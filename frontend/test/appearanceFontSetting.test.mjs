import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function read(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('appearance tab exposes font selector wired to app store font state', () => {
  const source = read('src/components/modals/tabs/AppearanceTab.vue')

  assert.equal(source.includes('label class="mb-2 block text-sm font-semibold text-[var(--color-text-main)]">Font</label>'), true)
  assert.equal(source.includes("import HeaderDropdown from '../../ui/HeaderDropdown.vue'"), true)
  assert.equal(source.includes(':model-value="activeFont"'), true)
  assert.equal(source.includes(':options="fontOptions"'), true)
  assert.equal(source.includes('@update:model-value="selectFont"'), true)
  assert.equal(source.includes('appStore.setUiFont(fontId)'), true)
})

test('app shell applies and persists font preference through font service', () => {
  const source = read('src/App.vue')

  assert.equal(source.includes("import { fontService } from './services/fontService'"), true)
  assert.equal(source.includes("import { normalizeFontId } from './constants/fonts'"), true)
  assert.equal(source.includes("document.documentElement.setAttribute('data-font', normalized)"), true)
  assert.equal(source.includes('() => appStore.uiFont'), true)
  assert.equal(source.includes('void fontService.saveFontPreference(normalized)'), true)
  assert.equal(source.includes('appStore.setUiFont(storedFont, { persist: false })'), true)
})

test('style and store include ubuntu font option', () => {
  const styleSource = read('src/style.css')
  const storeSource = read('src/stores/appStore.js')
  const fontsSource = read('src/constants/fonts.js')

  assert.equal(styleSource.includes('family=Ubuntu:wght@400;500;700'), true)
  assert.equal(styleSource.includes(':root[data-font="ubuntu"]'), true)
  assert.equal(styleSource.includes('--font-mono: "Ubuntu"'), false)
  assert.equal(fontsSource.includes("id: 'ubuntu'"), true)
  assert.equal(storeSource.includes('const uiFont = ref(DEFAULT_FONT_ID)'), true)
  assert.equal(storeSource.includes('function setUiFont(fontId, options = {}) {'), true)
})
