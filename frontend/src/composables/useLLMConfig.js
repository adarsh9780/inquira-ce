import { computed, ref } from 'vue'
import { apiService } from '../services/apiService'
import { extractApiErrorMessage } from '../utils/apiError'

const provider = ref(null)
const apiKey = ref('')
const ollamaBaseUrl = ref('http://localhost:11434')
const keyVerified = ref(false)
const mainModels = ref([])
const liteModels = ref([])
const modelsLoading = ref(false)
const mainModel = ref(null)
const liteModel = ref(null)

const providerCatalogs = ref({})
const apiKeyPresenceByProvider = ref({})
const selectedProviderApiKeyPresent = ref(false)
const keyMask = ref('')
const usingMaskedKey = ref(false)
const verifyLoading = ref(false)
const verifyError = ref('')
const verifyWarning = ref('')
const verifySuccess = ref('')
const refreshNotice = ref('')
const refreshLoading = ref(false)
const saveLoading = ref(false)
const showAllModels = ref(false)

const modelMetaByProvider = ref({})

function normalizeProvider(raw) {
  const value = String(raw || '').trim().toLowerCase()
  if (value === 'api') return 'openrouter'
  if (value === 'openai' || value === 'openrouter' || value === 'ollama') return value
  return 'openrouter'
}

function titleCaseWords(value) {
  return String(value || '')
    .replace(/[\/_-]+/g, ' ')
    .split(' ')
    .filter(Boolean)
    .map((token) => token.charAt(0).toUpperCase() + token.slice(1))
    .join(' ')
}

function toDisplayName(modelId, providerName) {
  const id = String(modelId || '').trim()
  if (!id) return 'Unknown Model'

  if (providerName === 'openrouter') {
    if (id.startsWith('openai/')) {
      return `${titleCaseWords(id.split('/', 2)[1])} (via OpenRouter)`
    }
    const parts = id.split('/')
    if (parts.length > 1) return titleCaseWords(parts[1])
  }

  if (id.includes('/')) {
    return titleCaseWords(id.split('/', 2)[1])
  }
  return titleCaseWords(id)
}

function inferRecommendedFor(modelId, mainSet, liteSet) {
  const id = String(modelId || '').trim()
  if (!id) return ['main']
  if (mainSet.has(id) && liteSet.has(id)) return ['both']
  if (liteSet.has(id)) return ['lite']
  if (mainSet.has(id)) return ['main']
  const lowered = id.toLowerCase()
  if (
    lowered.includes('mini') ||
    lowered.includes('nano') ||
    lowered.includes('lite') ||
    lowered.includes('haiku') ||
    lowered.includes('flash') ||
    lowered.includes(':2b') ||
    lowered.includes(':3b')
  ) {
    return ['lite']
  }
  return ['main']
}

function normalizeModelMetadata(providerName, catalog, mainIds, liteIds) {
  const rawEntries = Array.isArray(catalog?.models) ? catalog.models : []
  const mainSet = new Set(mainIds)
  const liteSet = new Set(liteIds)
  const map = new Map()

  for (const raw of rawEntries) {
    const id = String(raw?.id || '').trim()
    if (!id) continue
    const recommendedFor = Array.isArray(raw?.recommended_for) && raw.recommended_for.length
      ? raw.recommended_for.map((item) => String(item || '').trim().toLowerCase()).filter(Boolean)
      : inferRecommendedFor(id, mainSet, liteSet)
    const tags = Array.isArray(raw?.tags) && raw.tags.length
      ? raw.tags.map((item) => String(item || '').trim().toLowerCase()).filter(Boolean)
      : ['recommended']
    map.set(id, {
      id,
      display_name: String(raw?.display_name || toDisplayName(id, providerName)).trim(),
      provider: String(raw?.provider || providerName).trim() || providerName,
      context_window: Number(raw?.context_window || 0),
      recommended_for: recommendedFor.includes('both') ? ['both'] : Array.from(new Set(recommendedFor)),
      tags: tags.length ? Array.from(new Set(tags)) : ['recommended'],
    })
  }

  for (const id of [...mainIds, ...liteIds]) {
    if (map.has(id)) continue
    map.set(id, {
      id,
      display_name: toDisplayName(id, providerName),
      provider: providerName,
      context_window: 0,
      recommended_for: inferRecommendedFor(id, mainSet, liteSet),
      tags: ['recommended'],
    })
  }

  return Object.fromEntries(map)
}

function applyProviderModelState(providerName, prefs = {}, preserveSelection = true) {
  const normalized = normalizeProvider(providerName)
  const catalogs = prefs?.provider_model_catalogs && typeof prefs.provider_model_catalogs === 'object'
    ? prefs.provider_model_catalogs
    : providerCatalogs.value

  if (catalogs && typeof catalogs === 'object') {
    providerCatalogs.value = catalogs
  }

  const catalog = providerCatalogs.value?.[normalized] || {}
  const providerMain = Array.isArray(prefs?.provider_available_main_models)
    ? prefs.provider_available_main_models
    : Array.isArray(catalog?.main_models)
      ? catalog.main_models
      : []
  const providerLite = Array.isArray(prefs?.provider_available_lite_models)
    ? prefs.provider_available_lite_models
    : Array.isArray(catalog?.lite_models)
      ? catalog.lite_models
      : []

  const normalizedMain = Array.from(new Set(providerMain.map((item) => String(item || '').trim()).filter(Boolean)))
  const normalizedLite = Array.from(new Set(providerLite.map((item) => String(item || '').trim()).filter(Boolean)))

  mainModels.value = normalizedMain
  liteModels.value = normalizedLite.length ? normalizedLite : [...normalizedMain]

  const metadata = normalizeModelMetadata(normalized, catalog, mainModels.value, liteModels.value)
  modelMetaByProvider.value = {
    ...modelMetaByProvider.value,
    [normalized]: metadata,
  }

  const preferredMain = String(prefs?.selected_model || '').trim()
  const preferredLite = String(prefs?.selected_lite_model || '').trim()

  if (!preserveSelection || !mainModel.value || !mainModels.value.includes(mainModel.value)) {
    mainModel.value = mainModels.value.includes(preferredMain)
      ? preferredMain
      : (mainModels.value[0] || null)
  }

  if (!preserveSelection || !liteModel.value || !liteModels.value.includes(liteModel.value)) {
    liteModel.value = liteModels.value.includes(preferredLite)
      ? preferredLite
      : (liteModels.value[0] || null)
  }
}

function getModelMeta(providerName, modelId) {
  const normalized = normalizeProvider(providerName)
  return modelMetaByProvider.value?.[normalized]?.[modelId] || null
}

async function loadPreferences(providerHint = null, preserveSelection = false) {
  modelsLoading.value = true
  try {
    const response = await apiService.v1GetPreferences()
    const normalizedProvider = normalizeProvider(providerHint || response?.llm_provider)

    provider.value = normalizedProvider
    apiKeyPresenceByProvider.value = response?.api_key_present_by_provider || {}
    selectedProviderApiKeyPresent.value = !!response?.selected_provider_api_key_present
    verifyError.value = ''
    verifyWarning.value = ''
    verifySuccess.value = ''
    refreshNotice.value = ''

    if (selectedProviderApiKeyPresent.value && normalizedProvider !== 'ollama') {
      keyMask.value = 'sk-••••••••••••••••••••YzBp'
      apiKey.value = keyMask.value
      usingMaskedKey.value = true
    } else {
      keyMask.value = ''
      apiKey.value = ''
      usingMaskedKey.value = false
    }

    applyProviderModelState(normalizedProvider, response, preserveSelection)
    keyVerified.value = normalizedProvider === 'ollama' || !!selectedProviderApiKeyPresent.value

    return response
  } finally {
    modelsLoading.value = false
  }
}

function clearTransientMessages() {
  verifyError.value = ''
  verifyWarning.value = ''
  verifySuccess.value = ''
  refreshNotice.value = ''
}

function clearSensitiveState() {
  apiKey.value = ''
  keyMask.value = ''
  usingMaskedKey.value = false
  keyVerified.value = false
  verifyLoading.value = false
  saveLoading.value = false
  clearTransientMessages()
}

function setProvider(nextProvider) {
  const normalized = normalizeProvider(nextProvider)
  provider.value = normalized
  clearTransientMessages()

  const hasSavedKey = !!apiKeyPresenceByProvider.value?.[normalized]
  keyVerified.value = normalized === 'ollama' || hasSavedKey
  selectedProviderApiKeyPresent.value = hasSavedKey
  if (hasSavedKey && normalized !== 'ollama') {
    keyMask.value = 'sk-••••••••••••••••••••YzBp'
    apiKey.value = keyMask.value
    usingMaskedKey.value = true
  } else {
    keyMask.value = ''
    apiKey.value = ''
    usingMaskedKey.value = false
  }

  applyProviderModelState(normalized, {}, false)
}

function setApiKey(value) {
  apiKey.value = String(value || '')
  usingMaskedKey.value = false
  keyVerified.value = false
  verifySuccess.value = ''
  verifyError.value = ''
  verifyWarning.value = ''
}

async function verifyKey() {
  const selectedProvider = normalizeProvider(provider.value)
  clearTransientMessages()

  if (selectedProvider === 'ollama') {
    keyVerified.value = true
    return { ok: true, valid: true, error: '' }
  }

  if (usingMaskedKey.value && apiKey.value === keyMask.value) {
    keyVerified.value = true
    verifySuccess.value = 'Saved key is already configured.'
    return { ok: true, valid: true, error: '' }
  }

  const key = String(apiKey.value || '').trim()
  if (!key) {
    verifyError.value = 'Enter an API key to continue.'
    return { ok: false, valid: false, error: 'missing_key' }
  }

  verifyLoading.value = true
  try {
    const response = await apiService.v1VerifyApiKey(selectedProvider, key)
    if (response?.valid) {
      keyVerified.value = true
      verifySuccess.value = 'Key verified.'
      return { ok: true, valid: true, error: '' }
    }

    const code = String(response?.error || 'invalid_key').trim()
    if (code === 'quota_exceeded') {
      keyVerified.value = true
      verifyWarning.value = 'Key is valid but quota is exceeded.'
      return { ok: true, valid: false, error: code }
    }
    if (code === 'network_error') {
      verifyWarning.value = 'Could not reach provider - check your connection.'
      return { ok: false, valid: false, error: code }
    }

    verifyError.value = 'Invalid API key. Please check and try again.'
    return { ok: false, valid: false, error: code }
  } catch (error) {
    verifyWarning.value = 'Could not reach provider - check your connection.'
    return { ok: false, valid: false, error: 'network_error', detail: extractApiErrorMessage(error) }
  } finally {
    verifyLoading.value = false
  }
}

async function saveKey() {
  const selectedProvider = normalizeProvider(provider.value)
  if (selectedProvider === 'ollama') {
    return { ok: true }
  }

  if (usingMaskedKey.value && apiKey.value === keyMask.value) {
    return { ok: true }
  }

  const key = String(apiKey.value || '').trim()
  if (!key) {
    return { ok: false, error: 'missing_key' }
  }

  await apiService.v1SetApiKey(key, selectedProvider)
  apiKeyPresenceByProvider.value = {
    ...apiKeyPresenceByProvider.value,
    [selectedProvider]: true,
  }
  selectedProviderApiKeyPresent.value = true
  keyMask.value = 'sk-••••••••••••••••••••YzBp'
  apiKey.value = keyMask.value
  usingMaskedKey.value = true
  return { ok: true }
}

async function refreshModels({ background = false } = {}) {
  const selectedProvider = normalizeProvider(provider.value)
  const selectedMainBefore = mainModel.value
  const selectedLiteBefore = liteModel.value

  if (!background) {
    refreshLoading.value = true
    modelsLoading.value = true
    refreshNotice.value = ''
  }

  try {
    const payload = { provider: selectedProvider }
    if (selectedProvider === 'ollama') {
      payload.base_url = String(ollamaBaseUrl.value || '').trim() || 'http://localhost:11434'
    } else if (!usingMaskedKey.value) {
      const key = String(apiKey.value || '').trim()
      if (key) payload.api_key = key
    }

    const response = await apiService.v1RefreshProviderModels(payload)
    applyProviderModelState(selectedProvider, response, true)

    if (selectedMainBefore && mainModels.value.includes(selectedMainBefore)) {
      mainModel.value = selectedMainBefore
    }
    if (selectedLiteBefore && liteModels.value.includes(selectedLiteBefore)) {
      liteModel.value = selectedLiteBefore
    }

    if (response?.error === 'ollama_unreachable') {
      refreshNotice.value = `Ollama not detected at ${payload.base_url}. Is it running?`
      return { ok: false, error: 'ollama_unreachable', response }
    }

    refreshNotice.value = ''
    return { ok: true, response }
  } catch (_error) {
    refreshNotice.value = 'Using cached model list.'
    return { ok: false, error: 'refresh_failed' }
  } finally {
    if (!background) {
      refreshLoading.value = false
      modelsLoading.value = false
    }
  }
}

async function saveConfig() {
  const selectedProvider = normalizeProvider(provider.value)

  saveLoading.value = true
  try {
    if (selectedProvider !== 'ollama') {
      const keyResult = await saveKey()
      if (!keyResult.ok) {
        return { ok: false, error: keyResult.error || 'save_key_failed' }
      }
    }

    const payload = {
      llm_provider: selectedProvider,
      selected_model: String(mainModel.value || '').trim(),
      selected_lite_model: String(liteModel.value || '').trim(),
      selected_coding_model: String(mainModel.value || '').trim(),
      enabled_models: [...mainModels.value],
    }

    const response = await apiService.v1UpdatePreferences(payload)
    applyProviderModelState(selectedProvider, response, true)
    return { ok: true, response }
  } catch (error) {
    return { ok: false, error: extractApiErrorMessage(error, 'Failed to save configuration.') }
  } finally {
    saveLoading.value = false
  }
}

const providerLabel = computed(() => {
  if (provider.value === 'openai') return 'OpenAI'
  if (provider.value === 'openrouter') return 'OpenRouter'
  if (provider.value === 'ollama') return 'Ollama (local)'
  return 'OpenRouter'
})

const maskedKeySuffix = computed(() => {
  if (!keyMask.value) return 'Not saved'
  const tail = keyMask.value.replace(/\s+/g, '')
  return tail.slice(-4) || 'Saved'
})

const currentProviderModelMeta = computed(() => (
  modelMetaByProvider.value?.[normalizeProvider(provider.value)] || {}
))

export const useLLMConfig = () => {
  return {
    provider,
    apiKey,
    ollamaBaseUrl,
    keyVerified,
    mainModels,
    liteModels,
    modelsLoading,
    mainModel,
    liteModel,
    selectedProviderApiKeyPresent,
    keyMask,
    usingMaskedKey,
    verifyLoading,
    verifyError,
    verifyWarning,
    verifySuccess,
    refreshNotice,
    refreshLoading,
    saveLoading,
    showAllModels,
    providerLabel,
    maskedKeySuffix,
    currentProviderModelMeta,
    loadPreferences,
    setProvider,
    setApiKey,
    verifyKey,
    saveKey,
    refreshModels,
    saveConfig,
    getModelMeta,
    clearSensitiveState,
    clearTransientMessages,
    applyProviderModelState,
  }
}
