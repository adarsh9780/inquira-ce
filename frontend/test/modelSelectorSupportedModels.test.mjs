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

  assert.equal(source.includes('const fallbackMainModels = normalizeModelList(prefs?.provider_available_main_models)'), true)
  assert.equal(source.includes('availableModels.value = [...providerMainModels.value]'), true)
  assert.equal(source.includes('selectedCodingModel.value = selectedModel.value'), true)
  assert.equal(source.includes('if (typeof prefs?.terminal_risk_acknowledged === \'boolean\')'), true)
  assert.equal(source.includes('terminalConsentGranted.value = prefs.terminal_risk_acknowledged'), true)
  assert.equal(source.includes('terminal_risk_acknowledged: terminalConsentGranted.value'), true)
})
