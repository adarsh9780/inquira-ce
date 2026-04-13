import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function read(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('useLLMConfig composable exposes progressive setup state and actions', () => {
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
})

test('LLM settings tab uses 4 panel progressive flow with verify, refresh, and save controls', () => {
  const source = read('src/components/modals/tabs/LLMSettingsTab.vue')

  assert.equal(source.includes('Choose provider'), true)
  assert.equal(source.includes('OpenAI'), true)
  assert.equal(source.includes('OpenRouter'), true)
  assert.equal(source.includes('Ollama (local)'), true)

  assert.equal(source.includes('Verify & save key'), true)
  assert.equal(source.includes('Refresh model list'), true)
  assert.equal(source.includes('Show all models'), true)
  assert.equal(source.includes('Save configuration'), true)

  assert.equal(source.includes('async function verifyAndSave()'), true)
  assert.equal(source.includes('async function connectOllama()'), true)
  assert.equal(source.includes('async function refreshModelList()'), true)
  assert.equal(source.includes('async function saveConfiguration()'), true)
})
