import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app store persists and exposes data focus mode state', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/stores/appStore.js'), 'utf-8')

  assert.equal(source.includes('const isDataFocusMode = ref(false)'), true)
  assert.equal(source.includes('data_focus_mode: !!isDataFocusMode.value'), true)
  assert.equal(source.includes("if (typeof ui.data_focus_mode === 'boolean')"), true)
  assert.equal(source.includes('function setDataFocusMode(enabled) {'), true)
  assert.equal(source.includes('function toggleDataFocusMode() {'), true)
  assert.equal(source.includes('setDataFocusMode(!isDataFocusMode.value)'), true)
})
