import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('LLM settings expose opt-in data samples preference', () => {
  const tabPath = resolve(process.cwd(), 'src/components/modals/tabs/LLMSettingsTab.vue')
  const tabSource = readFileSync(tabPath, 'utf-8')

  assert.equal(tabSource.includes('v-model="allowLlmDataSamples"'), true)
  assert.equal(tabSource.includes('saveDataSamplesPreference'), true)
  assert.equal(tabSource.includes('dataSamplesMessage'), true)
  assert.equal(tabSource.includes('Allow bounded data samples in LLM prompts'), true)
  assert.equal(tabSource.includes('analyst-style markdown explanations instead of generic summaries'), true)
  assert.equal(tabSource.includes('enables insight-first result explanations'), false)
})

test('app store syncs LLM data samples preference with backend preferences', () => {
  const storePath = resolve(process.cwd(), 'src/stores/appStore.js')
  const storeSource = readFileSync(storePath, 'utf-8')

  assert.equal(storeSource.includes('const allowLlmDataSamples = ref(false)'), true)
  assert.equal(storeSource.includes('allow_llm_data_samples: allowLlmDataSamples.value'), true)
  assert.equal(storeSource.includes('prefs?.allow_llm_data_samples'), true)
  assert.equal(storeSource.includes('allowLlmDataSamples.value = prefs.allow_llm_data_samples'), true)
})

test('LLM config save paths persist bounded samples preference', () => {
  const configPath = resolve(process.cwd(), 'src/composables/useLLMConfig.js')
  const apiTabPath = resolve(process.cwd(), 'src/components/modals/ApiTab.vue')
  const configSource = readFileSync(configPath, 'utf-8')
  const apiTabSource = readFileSync(apiTabPath, 'utf-8')

  assert.equal(configSource.includes('async function saveDataSamplesPreference()'), true)
  assert.equal(configSource.includes('allow_llm_data_samples: Boolean(allowLlmDataSamples.value)'), true)
  assert.equal(configSource.includes('await saveDataSamplesPreference()'), true)
  assert.equal(apiTabSource.includes('allow_llm_data_samples: appStore.allowLlmDataSamples'), true)
})
