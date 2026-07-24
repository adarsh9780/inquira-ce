import { defineStore } from 'pinia'
import { ref } from 'vue'
import { DEFAULT_THEME_ID, THEME_OPTIONS, normalizeThemeId } from '../constants/themes'
import {
  APP_FONT_OPTIONS,
  CODE_FONT_OPTIONS,
  DEFAULT_APP_FONT_ID,
  DEFAULT_CODE_FONT_ID,
  normalizeAppFontId,
  normalizeCodeFontId,
} from '../constants/fonts'
import { preferencesApi } from '../api/preferences'

const DEFAULT_MODELS = [
  'google/gemini-3-flash-preview',
  'google/gemini-2.5-flash',
  'google/gemini-2.5-flash-lite',
  'openrouter/free',
]

export const usePreferencesStore = defineStore('preferences', () => {
  let persistChange: (() => void) | null = null
  const llmProvider = ref('openrouter')
  const availableProviders = ref(['openrouter', 'openai', 'anthropic', 'ollama'])
  const selectedModel = ref('google/gemini-2.5-flash')
  const selectedLiteModel = ref('google/gemini-2.5-flash-lite')
  const selectedCodingModel = ref('google/gemini-2.5-flash')
  const slowRequestWarningSeconds = ref(120)
  const availableModels = ref([...DEFAULT_MODELS])
  const providerMainModels = ref([...DEFAULT_MODELS])
  const providerLiteModels = ref(['google/gemini-2.5-flash-lite'])
  const providerModelSearchResults = ref<Record<string, string[]>>({})
  const providerModelSearchLoading = ref(false)
  const providerModelSearchQuery = ref('')
  const providerModelCatalogs = ref<Record<string, unknown>>({})
  const providerRequiresApiKey = ref(true)
  const apiKeyPresenceByProvider = ref<Record<string, boolean>>({})
  const selectedProviderApiKeyPresent = ref(false)
  const apiKey = ref('')
  const apiKeyConfigured = ref(false)
  const allowLlmDataSamples = ref(false)
  const uiTheme = ref(DEFAULT_THEME_ID)
  const availableThemes = ref(THEME_OPTIONS.map((theme) => ({ ...theme })))
  const uiFont = ref(DEFAULT_APP_FONT_ID)
  const availableFonts = ref(APP_FONT_OPTIONS.map((font) => ({ ...font })))
  const uiCodeFont = ref(DEFAULT_CODE_FONT_ID)
  const availableCodeFonts = ref(CODE_FONT_OPTIONS.map((font) => ({ ...font })))

  function configurePersistence(handler: (() => void) | null) {
    persistChange = handler
  }

  function setApiKey(key: unknown) {
    apiKey.value = String(key || '')
  }

  function setSelectedModel(model: unknown) {
    const value = String(model || '').trim()
    if (!value) return
    selectedModel.value = value
    if (!availableModels.value.includes(value)) availableModels.value = [value, ...availableModels.value]
    persistChange?.()
  }

  function normalizeModels(models: unknown, provider = '') {
    const prefix = String(provider || '').trim().toLowerCase()
    return [...new Set((Array.isArray(models) ? models : [])
      .map((value) => {
        if (typeof value === 'string') return value
        const record = (value || {}) as Record<string, unknown>
        return String(record.id || record.model_id || record.name || '')
      })
      .map((value) => String(value || '').trim())
      .filter((value) => value && (!prefix || !value.includes('/') || value.startsWith(`${prefix}/`) || prefix === 'openrouter')))]
  }

  function clearProviderModelSearchState() {
    providerModelSearchResults.value = {}
    providerModelSearchLoading.value = false
    providerModelSearchQuery.value = ''
  }

  function mergeProviderModelOptions(provider: unknown, results: unknown = []) {
    const normalizedProvider = String(provider || llmProvider.value).trim().toLowerCase()
    const models = normalizeModels(results, normalizedProvider)
    providerModelSearchResults.value = { ...providerModelSearchResults.value, [normalizedProvider]: models }
    if (normalizedProvider === llmProvider.value) {
      availableModels.value = [...new Set([...availableModels.value, ...models])]
    }
    return models
  }

  async function searchProviderModels(query: unknown, limit = 25) {
    const normalizedQuery = String(query || '').trim()
    const provider = String(llmProvider.value || '').trim().toLowerCase()
    providerModelSearchQuery.value = normalizedQuery
    if (normalizedQuery.length < 3) {
      providerModelSearchResults.value = { ...providerModelSearchResults.value, [provider]: [] }
      return []
    }
    providerModelSearchLoading.value = true
    try {
      const response = await preferencesApi.searchModels(provider, normalizedQuery, limit)
      const record = response as unknown as Record<string, unknown>
      return mergeProviderModelOptions(provider, Array.isArray(response) ? response : record?.models)
    } finally {
      providerModelSearchLoading.value = false
    }
  }

  function applyPreferencesResponse(response: unknown) {
    const prefs = (response || {}) as Record<string, any>
    llmProvider.value = String(prefs.provider || prefs.llm_provider || llmProvider.value)
    availableProviders.value = normalizeModels(prefs.available_providers || prefs.providers)
    if (availableProviders.value.length === 0) {
      availableProviders.value = ['openrouter', 'openai', 'anthropic', 'ollama']
    }
    selectedModel.value = String(prefs.main_model || prefs.selected_model || selectedModel.value)
    selectedLiteModel.value = String(prefs.lite_model || selectedLiteModel.value)
    selectedCodingModel.value = String(prefs.coding_model || selectedCodingModel.value)
    slowRequestWarningSeconds.value = Math.max(10, Number(prefs.slow_request_warning_seconds || 120))
    const models = normalizeModels(prefs.models || prefs.available_models, llmProvider.value)
    if (models.length) availableModels.value = models
    providerMainModels.value = normalizeModels(prefs.main_models || models, llmProvider.value)
    providerLiteModels.value = normalizeModels(prefs.lite_models || models, llmProvider.value)
    providerRequiresApiKey.value = prefs.provider_requires_api_key !== false
    apiKeyPresenceByProvider.value = prefs.api_key_presence_by_provider || {}
    selectedProviderApiKeyPresent.value = Boolean(
      prefs.api_key_configured ?? apiKeyPresenceByProvider.value[llmProvider.value],
    )
    apiKeyConfigured.value = selectedProviderApiKeyPresent.value
    allowLlmDataSamples.value = Boolean(prefs.allow_llm_data_samples)
    clearProviderModelSearchState()
    return prefs
  }

  async function loadUserPreferences(provider: unknown = null) {
    const response = await preferencesApi.get(provider)
    applyPreferencesResponse(response)
    return response
  }

  function reset() {
    llmProvider.value = 'openrouter'
    availableProviders.value = ['openrouter', 'openai', 'anthropic', 'ollama']
    selectedModel.value = 'google/gemini-2.5-flash'
    selectedLiteModel.value = 'google/gemini-2.5-flash-lite'
    selectedCodingModel.value = 'google/gemini-2.5-flash'
    slowRequestWarningSeconds.value = 120
    availableModels.value = [...DEFAULT_MODELS]
    providerMainModels.value = [...DEFAULT_MODELS]
    providerLiteModels.value = ['google/gemini-2.5-flash-lite']
    providerModelCatalogs.value = {}
    providerRequiresApiKey.value = true
    apiKeyPresenceByProvider.value = {}
    selectedProviderApiKeyPresent.value = false
    apiKey.value = ''
    apiKeyConfigured.value = false
    allowLlmDataSamples.value = false
    clearProviderModelSearchState()
  }

  function setUiTheme(themeId: unknown, options: { persist?: boolean } = {}) {
    const normalized = normalizeThemeId(themeId)
    if (uiTheme.value === normalized) return
    uiTheme.value = normalized
    if (options.persist !== false) persistChange?.()
  }

  function setUiFont(fontId: unknown, options: { persist?: boolean } = {}) {
    const normalized = normalizeAppFontId(fontId)
    if (uiFont.value === normalized) return
    uiFont.value = normalized
    if (options.persist !== false) persistChange?.()
  }

  function setUiCodeFont(fontId: unknown, options: { persist?: boolean } = {}) {
    const normalized = normalizeCodeFontId(fontId)
    if (uiCodeFont.value === normalized) return
    uiCodeFont.value = normalized
    if (options.persist !== false) persistChange?.()
  }

  return {
    llmProvider,
    availableProviders,
    selectedModel,
    selectedLiteModel,
    selectedCodingModel,
    slowRequestWarningSeconds,
    availableModels,
    providerMainModels,
    providerLiteModels,
    providerModelSearchResults,
    providerModelSearchLoading,
    providerModelSearchQuery,
    providerModelCatalogs,
    providerRequiresApiKey,
    apiKeyPresenceByProvider,
    selectedProviderApiKeyPresent,
    apiKey,
    apiKeyConfigured,
    allowLlmDataSamples,
    uiTheme,
    availableThemes,
    uiFont,
    availableFonts,
    uiCodeFont,
    availableCodeFonts,
    configurePersistence,
    setApiKey,
    setSelectedModel,
    clearProviderModelSearchState,
    mergeProviderModelOptions,
    searchProviderModels,
    applyPreferencesResponse,
    loadUserPreferences,
    reset,
    setUiTheme,
    setUiFont,
    setUiCodeFont,
  }
})
