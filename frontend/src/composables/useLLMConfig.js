import { computed, ref, watch } from 'vue'
import { apiService } from '../services/apiService'
import { extractApiErrorMessage } from '../utils/apiError'
import { useAppStore } from '../stores/appStore'

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
const llmTemperature = ref(0.7)
const llmMaxTokens = ref(4096)
const llmTopP = ref(1)
const llmTopK = ref(0)
const llmFrequencyPenalty = ref(0)
const llmPresencePenalty = ref(0)
const slowRequestWarningSeconds = ref(120)

const modelMetaByProvider = ref({})
let appStore = null

function getAppStore() {
  if (!appStore) {
    appStore = useAppStore()
  }
  return appStore
}

function normalizeProvider(raw) {
  const value = String(raw || '').trim().toLowerCase()
  if (value === 'api') return 'openrouter'
  if (value === 'openai' || value === 'openrouter' || value === 'ollama') return value
  return 'openrouter'
}

function modelAllowedForProvider(providerName, modelId) {
  const normalizedProvider = normalizeProvider(providerName)
  const value = String(modelId || '').trim().toLowerCase()
  if (!value) return false
  if (normalizedProvider !== 'ollama' && value.includes(':cloud')) {
    return false
  }
  return true
}

function normalizeModelIds(providerName, models) {
  const seen = new Set()
  const cleaned = []
  const source = Array.isArray(models) ? models : []
  for (const item of source) {
    const value = String(item || '').trim()
    if (!value || seen.has(value)) continue
    if (!modelAllowedForProvider(providerName, value)) continue
    seen.add(value)
    cleaned.push(value)
  }
  return cleaned
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
    if (!modelAllowedForProvider(providerName, id)) continue
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

function syncProviderStateToAppStore(providerName) {
  const store = getAppStore()
  if (!store) return

  const normalized = normalizeProvider(providerName)
  const nextMainModels = [...mainModels.value]
  const nextLiteModels = [...liteModels.value]
  const selectedMain = String(mainModel.value || '').trim()
  const selectedLite = String(liteModel.value || '').trim()

  // Keep provider-scoped model lists synchronized in Pinia so all consumers refresh.
  store.llmProvider = normalized
  store.providerMainModels = nextMainModels
  store.providerLiteModels = nextLiteModels

  if (providerCatalogs.value && typeof providerCatalogs.value === 'object') {
    store.providerModelCatalogs = providerCatalogs.value
  }

  if (selectedMain) {
    store.selectedModel = selectedMain
    store.selectedCodingModel = selectedMain
  }
  if (selectedLite) {
    store.selectedLiteModel = selectedLite
  }

  store.providerRequiresApiKey = normalized !== 'ollama'
  store.selectedProviderApiKeyPresent = !!apiKeyPresenceByProvider.value?.[normalized]

  if (typeof store.clearProviderModelSearchState === 'function') {
    store.clearProviderModelSearchState()
  }
  if (typeof store.mergeProviderModelOptions === 'function') {
    store.mergeProviderModelOptions(normalized, [])
  } else {
    store.availableModels = nextMainModels
  }
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
  const responseProvider = normalizeProvider(prefs?.llm_provider)
  const useResponseModelLists = responseProvider === normalized
  const providerMain = useResponseModelLists && Array.isArray(prefs?.provider_available_main_models)
    ? prefs.provider_available_main_models
    : Array.isArray(catalog?.main_models)
      ? catalog.main_models
      : []
  const providerLite = useResponseModelLists && Array.isArray(prefs?.provider_available_lite_models)
    ? prefs.provider_available_lite_models
    : Array.isArray(catalog?.lite_models)
      ? catalog.lite_models
      : []

  const normalizedMain = normalizeModelIds(normalized, providerMain)
  const normalizedLite = normalizeModelIds(normalized, providerLite)

  mainModels.value = normalizedMain
  liteModels.value = normalizedLite.length ? normalizedLite : [...normalizedMain]

  const metadata = normalizeModelMetadata(normalized, catalog, mainModels.value, liteModels.value)
  modelMetaByProvider.value = {
    ...modelMetaByProvider.value,
    [normalized]: metadata,
  }

  const preferredMain = useResponseModelLists
    ? String(prefs?.selected_model || '').trim()
    : String(catalog?.default_main_model || '').trim()
  const preferredLite = useResponseModelLists
    ? String(prefs?.selected_lite_model || '').trim()
    : String(catalog?.default_lite_model || '').trim()

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

  if (normalized === 'ollama') {
    const catalogBaseUrl = String(catalog?.base_url || '').trim()
    if (catalogBaseUrl) {
      ollamaBaseUrl.value = catalogBaseUrl
    }
  }

  syncProviderStateToAppStore(normalized)
}

function getModelMeta(providerName, modelId) {
  const normalized = normalizeProvider(providerName)
  return modelMetaByProvider.value?.[normalized]?.[modelId] || null
}

async function loadPreferences(providerHint = null, preserveSelection = false) {
  modelsLoading.value = true
  try {
    const response = await apiService.v1GetPreferences(providerHint)
    const normalizedProvider = normalizeProvider(providerHint || response?.llm_provider)

    provider.value = normalizedProvider
    apiKeyPresenceByProvider.value = response?.api_key_present_by_provider || {}
    selectedProviderApiKeyPresent.value = !!apiKeyPresenceByProvider.value?.[normalizedProvider]
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
    llmTemperature.value = Number(response?.llm_temperature ?? 0.7)
    llmMaxTokens.value = Number(response?.llm_max_tokens ?? 4096)
    llmTopP.value = Number(response?.llm_top_p ?? 1)
    llmTopK.value = Number(response?.llm_top_k ?? 0)
    llmFrequencyPenalty.value = Number(response?.llm_frequency_penalty ?? 0)
    llmPresencePenalty.value = Number(response?.llm_presence_penalty ?? 0)
    slowRequestWarningSeconds.value = Number(response?.slow_request_warning_seconds ?? 120)
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

function resetForAuthBoundary() {
  provider.value = null
  mainModels.value = []
  liteModels.value = []
  mainModel.value = null
  liteModel.value = null
  providerCatalogs.value = {}
  apiKeyPresenceByProvider.value = {}
  selectedProviderApiKeyPresent.value = false
  modelMetaByProvider.value = {}
  clearSensitiveState()
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
  mainModels.value = []
  liteModels.value = []
  mainModel.value = null
  liteModel.value = null
}

function setApiKey(value) {
  const nextValue = String(value || '')
  apiKey.value = nextValue
  usingMaskedKey.value = !!keyMask.value && nextValue === keyMask.value
  keyVerified.value = usingMaskedKey.value
  verifySuccess.value = ''
  verifyError.value = ''
  verifyWarning.value = ''
}

function setMainModel(value) {
  const nextValue = String(value || '').trim()
  mainModel.value = nextValue || null
  const store = getAppStore()
  if (store && typeof store.setSelectedModel === 'function') {
    store.setSelectedModel(nextValue)
  }
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
      return { ok: true, valid: true, error: '' }
    }

    const code = String(response?.error || 'invalid_key').trim()
    if (code === 'quota_exceeded') {
      verifyError.value = 'Key is valid but quota is exceeded for this provider.'
      return { ok: false, valid: false, error: code }
    }
    if (code === 'network_error') {
      verifyError.value = 'Could not reach provider. Check your connection and try again.'
      return { ok: false, valid: false, error: code }
    }

    verifyError.value = 'Invalid API key. Please check and try again.'
    return { ok: false, valid: false, error: code }
  } catch (error) {
    verifyError.value = 'Could not reach provider. Check your connection and try again.'
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

  await apiService.v1SetApiKey({
    provider: selectedProvider,
    api_key: key,
  })
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

async function deleteKey() {
  const selectedProvider = normalizeProvider(provider.value)
  if (selectedProvider === 'ollama') {
    return { ok: false, error: 'provider_has_no_key' }
  }

  await apiService.v1DeleteApiKey(selectedProvider)
  apiKeyPresenceByProvider.value = {
    ...apiKeyPresenceByProvider.value,
    [selectedProvider]: false,
  }
  selectedProviderApiKeyPresent.value = false
  keyMask.value = ''
  apiKey.value = ''
  usingMaskedKey.value = false
  keyVerified.value = false
  clearTransientMessages()
  verifySuccess.value = 'Saved key removed'
  return { ok: true }
}

async function verifyAndSaveKey() {
  const selectedProvider = normalizeProvider(provider.value)
  clearTransientMessages()

  if (selectedProvider === 'ollama') {
    keyVerified.value = true
    const refreshed = await refreshModels({ background: true })
    return refreshed.ok
      ? { ok: true }
      : { ok: false, stage: 'refresh_models', error: refreshed.error || 'refresh_failed' }
  }

  const verifyResult = await verifyKey()
  if (!verifyResult.ok) {
    return { ok: false, stage: 'verify', error: verifyResult.error || 'verify_failed' }
  }

  const saveResult = await saveKey()
  if (!saveResult.ok) {
    return { ok: false, stage: 'save_key', error: saveResult.error || 'save_key_failed' }
  }

  verifySuccess.value = 'Key verified'
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

  try {
    const enteredKey = String(apiKey.value || '').trim()
    const hasNewUnmaskedKey = selectedProvider !== 'ollama' && !usingMaskedKey.value && !!enteredKey

    if (hasNewUnmaskedKey) {
      const verifyResult = await verifyKey()
      if (!verifyResult.ok) {
        return { ok: false, stage: 'verify', error: verifyResult.error || 'verify_failed' }
      }
    }

    saveLoading.value = true
    const payload = {
      provider: selectedProvider,
      selected_model: String(mainModel.value || '').trim(),
      selected_lite_model: String(liteModel.value || '').trim(),
      selected_coding_model: String(mainModel.value || '').trim(),
      llm_temperature: Number(llmTemperature.value),
      llm_max_tokens: Number(llmMaxTokens.value),
      llm_top_p: Number(llmTopP.value),
      llm_top_k: Number(llmTopK.value),
      llm_frequency_penalty: Number(llmFrequencyPenalty.value),
      llm_presence_penalty: Number(llmPresencePenalty.value),
      slow_request_warning_seconds: Number(slowRequestWarningSeconds.value),
    }
    if (selectedProvider === 'ollama') {
      payload.base_url = String(ollamaBaseUrl.value || '').trim() || 'http://localhost:11434'
    }
    if (hasNewUnmaskedKey) {
      payload.api_key = enteredKey
    }

    await apiService.v1SetApiKey(payload)
    const response = await loadPreferences(selectedProvider, true)
    return { ok: true, response }
  } catch (error) {
    return {
      ok: false,
      stage: 'save_configuration',
      error: extractApiErrorMessage(error, 'Failed to save configuration.'),
    }
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
  appStore = getAppStore()

  watch(
    () => getAppStore().selectedModel,
    (nextValue) => {
      const store = getAppStore()
      const normalizedProvider = normalizeProvider(provider.value)
      if (!normalizedProvider) return
      if (normalizedProvider !== normalizeProvider(store.llmProvider)) return
      const nextModel = String(nextValue || '').trim()
      if (nextModel && nextModel !== mainModel.value) {
        mainModel.value = nextModel
      }
    }
  )

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
    llmTemperature,
    llmMaxTokens,
    llmTopP,
    llmTopK,
    llmFrequencyPenalty,
    llmPresencePenalty,
    slowRequestWarningSeconds,
    providerLabel,
    maskedKeySuffix,
    currentProviderModelMeta,
    loadPreferences,
    setProvider,
    setApiKey,
    setMainModel,
    verifyKey,
    saveKey,
    verifyAndSaveKey,
    deleteKey,
    refreshModels,
    saveConfig,
    getModelMeta,
    clearSensitiveState,
    resetForAuthBoundary,
    clearTransientMessages,
    applyProviderModelState,
  }
}
