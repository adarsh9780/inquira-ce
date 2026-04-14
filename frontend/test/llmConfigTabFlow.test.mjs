import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function read(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('useLLMConfig composable exposes provider-aware save flow and advanced fields', () => {
  const source = read('src/composables/useLLMConfig.js')

  assert.equal(source.includes('const provider = ref(null)'), true)
  assert.equal(source.includes("const apiKey = ref('')"), true)
  assert.equal(source.includes("const ollamaBaseUrl = ref('http://localhost:11434')"), true)
  assert.equal(source.includes('const keyVerified = ref(false)'), true)
  assert.equal(source.includes('const mainModels = ref([])'), true)
  assert.equal(source.includes('const liteModels = ref([])'), true)
  assert.equal(source.includes('const modelsLoading = ref(false)'), true)
  assert.equal(source.includes('const mainModel = ref(null)'), true)
  assert.equal(source.includes('const liteModel = ref(null)'), true)
  assert.equal(source.includes('const llmTemperature = ref(0.7)'), true)
  assert.equal(source.includes('const llmMaxTokens = ref(4096)'), true)
  assert.equal(source.includes('const llmTopP = ref(1)'), true)
  assert.equal(source.includes('const llmTopK = ref(0)'), true)
  assert.equal(source.includes('const llmFrequencyPenalty = ref(0)'), true)
  assert.equal(source.includes('const llmPresencePenalty = ref(0)'), true)

  assert.equal(source.includes('async function verifyKey()'), true)
  assert.equal(source.includes('async function saveKey()'), true)
  assert.equal(source.includes('async function verifyAndSaveKey()'), true)
  assert.equal(source.includes('async function refreshModels({ background = false } = {})'), true)
  assert.equal(source.includes('async function saveConfig()'), true)
  assert.equal(source.includes('function clearSensitiveState()'), true)
  assert.equal(source.includes("const response = await apiService.v1GetPreferences(providerHint)"), true)
  assert.equal(source.includes('selectedProviderApiKeyPresent.value = !!apiKeyPresenceByProvider.value?.[normalizedProvider]'), true)
  assert.equal(source.includes("return { ok: false, stage: 'verify', error: verifyResult.error || 'verify_failed' }"), true)
  assert.equal(source.includes("const hasNewUnmaskedKey = selectedProvider !== 'ollama' && !usingMaskedKey.value && !!enteredKey"), true)
  assert.equal(source.includes('await apiService.v1SetApiKey(payload)'), true)
  assert.equal(source.includes('llm_temperature: Number(llmTemperature.value)'), true)
  assert.equal(source.includes('llm_max_tokens: Number(llmMaxTokens.value)'), true)
  assert.equal(source.includes('llm_top_k: Number(llmTopK.value)'), true)
  assert.equal(source.includes('await loadPreferences(selectedProvider, true)'), true)
})

test('LLM settings tab uses provider dropdown, searchable model selects, and advanced controls', () => {
  const source = read('src/components/modals/tabs/LLMSettingsTab.vue')

  assert.equal(source.includes('@change="handleProviderSelect($event.target.value)"'), true)
  assert.equal(source.includes('Provider'), true)
  assert.equal(source.includes('OpenAI'), true)
  assert.equal(source.includes('OpenRouter'), true)
  assert.equal(source.includes('Ollama (local)'), true)

  assert.equal(source.includes('Verify &amp; save key'), true)
  assert.equal(source.includes('Refresh model list'), true)
  assert.equal(source.includes('Show all models'), true)
  assert.equal(source.includes('Save configuration'), true)
  assert.equal(source.includes('Configuration ready'), false)
  assert.equal(source.includes('Update key'), false)
  assert.equal(source.includes('@click="openPanel'), false)
  assert.equal(source.includes('v-for="card in providerCards"'), false)
  assert.equal(source.includes('<HeaderDropdown'), true)
  assert.equal(source.includes('max-options-without-search="100"'), true)
  assert.equal(source.includes('v-model="mainSearch"'), false)
  assert.equal(source.includes('v-model="liteSearch"'), false)
  assert.equal(source.includes('Advanced settings'), true)
  assert.equal(source.includes('Temperature'), true)
  assert.equal(source.includes('Max tokens'), true)
  assert.equal(source.includes('Top K'), true)
  assert.equal(source.includes('Frequency penalty'), true)
  assert.equal(source.includes('Presence penalty'), true)
  assert.equal(source.includes('Reset to defaults'), true)

  assert.equal(source.includes('async function handleProviderSelect(nextProvider)'), true)
  assert.equal(source.includes('async function handleVerifyAndSaveKey()'), true)
  assert.equal(source.includes('async function refreshModelList()'), true)
  assert.equal(source.includes('async function saveConfiguration()'), true)
})

test('HeaderDropdown supports limiting default visible options before search', () => {
  const source = read('src/components/ui/HeaderDropdown.vue')

  assert.equal(source.includes('maxOptionsWithoutSearch'), true)
  assert.equal(source.includes('return options.slice(0, maxCount)'), true)
})
