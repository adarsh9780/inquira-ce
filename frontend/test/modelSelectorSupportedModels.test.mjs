import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('model selector accepts injected model options prop', () => {
  const path = resolve(process.cwd(), 'src/components/ui/ModelSelector.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('modelOptions'), true)
  assert.equal(source.includes('const availableModels = computed(() => {'), true)
  assert.equal(source.includes('const source = Array.isArray(props.modelOptions) && props.modelOptions.length'), true)
})

test('app store reads available models from v1 preferences payload', () => {
  const path = resolve(process.cwd(), 'src/stores/appStore.js')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('if (Array.isArray(prefs?.available_models) && prefs.available_models.length)'), true)
  assert.equal(source.includes('availableModels.value = prefs.available_models'), true)
})
