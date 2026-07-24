import { computed, ref, watch } from 'vue'
import { modelConnectionService } from '../services/modelConnectionService'
import { extractApiErrorMessage } from '../utils/apiError'
import { usePreferencesStore } from '../stores/preferencesStore'

type Provider = 'openai' | 'openrouter' | 'ollama'
type RecordValue = Record<string, unknown>

interface ModelMetadata {
  id: string
  display_name: string
  provider: string
  context_window: number
  recommended_for: string[]
  tags: string[]
}

interface ProviderCatalog extends RecordValue {
  models?: unknown[]
  main_models?: unknown[]
  lite_models?: unknown[]
  default_main_model?: unknown
  default_lite_model?: unknown
  base_url?: unknown
}

type ProviderCatalogs = Partial<Record<Provider, ProviderCatalog>>
type ProviderModelMetadata = Partial<Record<Provider, Record<string, ModelMetadata>>>

function asRecord(value: unknown): RecordValue {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as RecordValue
    : {}
}

const provider = ref<Provider | null>(null)
const apiKey = ref('')
const ollamaBaseUrl = ref('http://localhost:11434')
const keyVerified = ref(false)
const mainModels = ref<string[]>([])
const liteModels = ref<string[]>([])
const modelsLoading = ref(false)
const mainModel = ref<string | null>(null)
const liteModel = ref<string | null>(null)

const providerCatalogs = ref<ProviderCatalogs>({})
const apiKeyPresenceByProvider = ref<Partial<Record<Provider, boolean>>>({})
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
const allowLlmDataSamples = ref(false)

const modelMetaByProvider = ref<ProviderModelMetadata>({})
let preferencesStore: ReturnType<typeof usePreferencesStore> | null = null

function getPreferencesStore(): ReturnType<typeof usePreferencesStore> {
  if (!preferencesStore) {
    preferencesStore = usePreferencesStore()
  }
  return preferencesStore
}

function normalizeProvider(raw: unknown): Provider {
  const value = String(raw || '').trim().toLowerCase()
  if (value === 'api') return 'openrouter'
  if (value === 'openai' || value === 'openrouter' || value === 'ollama') return value
  return 'openrouter'
}

function modelAllowedForProvider(providerName: unknown, modelId: unknown): boolean {
  const normalizedProvider = normalizeProvider(providerName)
  const value = String(modelId || '').trim().toLowerCase()
  if (!value) return false
  if (normalizedProvider !== 'ollama' && value.includes(':cloud')) {
    return false
  }
  return true
}

function normalizeModelIds(providerName: unknown, models: unknown): string[] {
  const seen = new Set<string>()
  const cleaned: string[] = []
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

function titleCaseWords(value: unknown): string {
  return String(value || '')
    .replace(/[\/_-]+/g, ' ')
    .split(' ')
    .filter(Boolean)
    .map((token: string) => token.charAt(0).toUpperCase() + token.slice(1))
    .join(' ')
}

function toDisplayName(modelId: unknown, providerName: Provider): string {
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

function inferRecommendedFor(
  modelId: unknown,
  mainSet: Set<string>,
  liteSet: Set<string>,
): string[] {
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

function normalizeModelMetadata(
  providerName: Provider,
  catalog: ProviderCatalog,
  mainIds: string[],
  liteIds: string[],
): Record<string, ModelMetadata> {
  const rawEntries = Array.isArray(catalog.models) ? catalog.models : []
  const mainSet = new Set(mainIds)
  const liteSet = new Set(liteIds)
  const map = new Map<string, ModelMetadata>()

  for (const rawValue of rawEntries) {
    const raw = asRecord(rawValue)
    const id = String(raw.id || '').trim()
    if (!id) continue
    if (!modelAllowedForProvider(providerName, id)) continue
    const recommendedFor = Array.isArray(raw.recommended_for) && raw.recommended_for.length
      ? raw.recommended_for.map((item) => String(item || '').trim().toLowerCase()).filter(Boolean)
      : inferRecommendedFor(id, mainSet, liteSet)
    const tags = Array.isArray(raw.tags) && raw.tags.length
      ? raw.tags.map((item) => String(item || '').trim().toLowerCase()).filter(Boolean)
      : ['recommended']
    map.set(id, {
      id,
      display_name: String(raw.display_name || toDisplayName(id, providerName)).trim(),
      provider: String(raw.provider || providerName).trim() || providerName,
      context_window: Number(raw.context_window || 0),
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

function syncProviderStateToAppStore(providerName: unknown): void {
  const store = getPreferencesStore()
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

function applyProviderModelState(
  providerName: unknown,
  prefsValue: unknown = {},
  preserveSelection = true,
): void {
  const prefs = asRecord(prefsValue)
  const normalized = normalizeProvider(providerName)
  const catalogs = prefs.provider_model_catalogs && typeof prefs.provider_model_catalogs === 'object'
    ? prefs.provider_model_catalogs as ProviderCatalogs
    : providerCatalogs.value

  if (catalogs && typeof catalogs === 'object') {
    providerCatalogs.value = catalogs
  }

  const catalog = providerCatalogs.value[normalized] || {}
  const responseProvider = normalizeProvider(prefs.llm_provider)
  const useResponseModelLists = responseProvider === normalized
  const providerMain = useResponseModelLists && Array.isArray(prefs.provider_available_main_models)
    ? prefs.provider_available_main_models
    : Array.isArray(catalog?.main_models)
      ? catalog.main_models
      : []
  const providerLite = useResponseModelLists && Array.isArray(prefs.provider_available_lite_models)
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

function getModelMeta(providerName: unknown, modelId: string): ModelMetadata | null {
  const normalized = normalizeProvider(providerName)
  return modelMetaByProvider.value?.[normalized]?.[modelId] || null
}

async function loadPreferences(providerHint: unknown = null, preserveSelection = false) {
  modelsLoading.value = true
  try {
    const response = await modelConnectionService.getPreferences(providerHint)
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
    allowLlmDataSamples.value = Boolean(response?.allow_llm_data_samples)
    keyVerified.value = normalizedProvider === 'ollama' || !!selectedProviderApiKeyPresent.value

    return response
  } finally {
    modelsLoading.value = false
  }
}

function clearTransientMessages(): void {
  verifyError.value = ''
  verifyWarning.value = ''
  verifySuccess.value = ''
  refreshNotice.value = ''
}

function clearSensitiveState(): void {
  apiKey.value = ''
  keyMask.value = ''
  usingMaskedKey.value = false
  keyVerified.value = false
  verifyLoading.value = false
  saveLoading.value = false
  clearTransientMessages()
}

function resetForAuthBoundary(): void {
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

function setProvider(nextProvider: unknown): void {
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

function setApiKey(value: unknown): void {
  const nextValue = String(value || '')
  apiKey.value = nextValue
  usingMaskedKey.value = !!keyMask.value && nextValue === keyMask.value
  keyVerified.value = usingMaskedKey.value
  verifySuccess.value = ''
  verifyError.value = ''
  verifyWarning.value = ''
}

function setMainModel(value: unknown): void {
  const nextValue = String(value || '').trim()
  mainModel.value = nextValue || null
  const store = getPreferencesStore()
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
    const response = await modelConnectionService.verifyKey(selectedProvider, key)
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

  const response = await modelConnectionService.setApiKey({
    provider: selectedProvider,
    api_key: key,
    allow_llm_data_samples: Boolean(allowLlmDataSamples.value),
  })
  apiKeyPresenceByProvider.value = {
    ...apiKeyPresenceByProvider.value,
    [selectedProvider]: true,
  }
  selectedProviderApiKeyPresent.value = true
  if (response && typeof response === 'object') {
    applyProviderModelState(selectedProvider, response, true)
  }
  keyMask.value = 'sk-••••••••••••••••••••YzBp'
  apiKey.value = keyMask.value
  usingMaskedKey.value = true
  return { ok: true, response }
}

async function saveDataSamplesPreference() {
  const response = await modelConnectionService.updatePreferences({
    allow_llm_data_samples: Boolean(allowLlmDataSamples.value),
  })
  const store = getPreferencesStore()
  if (response && store && typeof store.applyPreferencesResponse === 'function') {
    store.applyPreferencesResponse(response)
  }
  return response
}

async function deleteKey() {
  const selectedProvider = normalizeProvider(provider.value)
  if (selectedProvider === 'ollama') {
    return { ok: false, error: 'provider_has_no_key' }
  }

  await modelConnectionService.deleteApiKey(selectedProvider)
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

  await saveDataSamplesPreference()
  verifySuccess.value = 'Key verified'
  return { ok: true }
}

async function refreshModels({ background = false }: { background?: boolean } = {}) {
  const selectedProvider = normalizeProvider(provider.value)
  const selectedMainBefore = mainModel.value
  const selectedLiteBefore = liteModel.value

  if (!background) {
    refreshLoading.value = true
    modelsLoading.value = true
    refreshNotice.value = ''
  }

  try {
    const payload: RecordValue = { provider: selectedProvider }
    if (selectedProvider === 'ollama') {
      payload.base_url = String(ollamaBaseUrl.value || '').trim() || 'http://localhost:11434'
    } else if (!usingMaskedKey.value) {
      const key = String(apiKey.value || '').trim()
      if (key) payload.api_key = key
    }

    const response = await modelConnectionService.refreshModels(payload)
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
    const hasSavedProviderKey = selectedProvider === 'ollama' || !!selectedProviderApiKeyPresent.value

    if (hasNewUnmaskedKey) {
      const verifyResult = await verifyKey()
      if (!verifyResult.ok) {
        return { ok: false, stage: 'verify', error: verifyResult.error || 'verify_failed' }
      }
    }

    saveLoading.value = true
    const preferencePayload = {
      llm_provider: selectedProvider,
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
      allow_llm_data_samples: Boolean(allowLlmDataSamples.value),
    }

    if (selectedProvider === 'ollama' || hasNewUnmaskedKey) {
      const securePayload: RecordValue = {
        provider: selectedProvider,
        ...preferencePayload,
      }
      if (selectedProvider === 'ollama') {
        securePayload.base_url = String(ollamaBaseUrl.value || '').trim() || 'http://localhost:11434'
      }
      if (hasNewUnmaskedKey) {
        securePayload.api_key = enteredKey
      }
      await modelConnectionService.setApiKey(securePayload)
    } else {
      if (!hasSavedProviderKey) {
        return {
          ok: false,
          stage: 'save_configuration',
          error: `Save a ${providerLabel.value} API key before updating model preferences.`,
        }
      }
      await modelConnectionService.updatePreferences(preferencePayload)
    }
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
  preferencesStore = getPreferencesStore()

  watch(
    () => getPreferencesStore().selectedModel,
    (nextValue) => {
      const store = getPreferencesStore()
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
    allowLlmDataSamples,
    providerLabel,
    maskedKeySuffix,
    currentProviderModelMeta,
    loadPreferences,
    setProvider,
    setApiKey,
    setMainModel,
    verifyKey,
    saveKey,
    saveDataSamplesPreference,
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
