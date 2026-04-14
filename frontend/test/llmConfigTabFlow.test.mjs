import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function read(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('useLLMConfig composable exposes unified save flow actions', () => {
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

  assert.equal(source.includes('async function verifyKey()'), true)
  assert.equal(source.includes('async function saveKey()'), true)
  assert.equal(source.includes('async function refreshModels({ background = false } = {})'), true)
  assert.equal(source.includes('async function saveConfig()'), true)
  assert.equal(source.includes('function clearSensitiveState()'), true)
  assert.equal(source.includes("const response = await apiService.v1GetPreferences(providerHint)"), true)
  assert.equal(source.includes('selectedProviderApiKeyPresent.value = !!apiKeyPresenceByProvider.value?.[normalizedProvider]'), true)
  assert.equal(source.includes("return { ok: false, stage: 'verify', error: verifyResult.error || 'verify_failed' }"), true)
})

test('LLM settings tab renders flat sections and a single save action', () => {
  const source = read('src/components/modals/tabs/LLMSettingsTab.vue')

  assert.equal(source.includes('Choose provider'), true)
  assert.equal(source.includes('OpenAI'), true)
  assert.equal(source.includes('OpenRouter'), true)
  assert.equal(source.includes('Ollama (local)'), true)

  assert.equal(source.includes('Key will be verified on save'), true)
  assert.equal(source.includes('Refresh model list'), true)
  assert.equal(source.includes('Show all models'), true)
  assert.equal(source.includes('Save configuration'), true)
  assert.equal(source.includes('Configuration ready'), false)
  assert.equal(source.includes('Update key'), false)
  assert.equal(source.includes('@click="openPanel'), false)
  assert.equal(source.includes('v-for="card in providerCards"'), false)
  assert.equal(source.includes('@change="handleProviderSelect($event.target.value)"'), true)
  assert.equal(source.includes('<HeaderDropdown'), true)
  assert.equal(source.includes('max-options-without-search="100"'), true)
  assert.equal(source.includes('v-model="mainSearch"'), false)
  assert.equal(source.includes('v-model="liteSearch"'), false)

  assert.equal(source.includes('async function handleProviderSelect(nextProvider)'), true)
  assert.equal(source.includes('async function refreshModelList()'), true)
  assert.equal(source.includes('async function saveConfiguration()'), true)
})

test('HeaderDropdown supports limiting default visible options before search', () => {
  const source = read('src/components/ui/HeaderDropdown.vue')

  assert.equal(source.includes('maxOptionsWithoutSearch'), true)
  assert.equal(source.includes('return options.slice(0, maxCount)'), true)
})
