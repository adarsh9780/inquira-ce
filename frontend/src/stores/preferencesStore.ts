import { defineStore } from 'pinia'
import { ref } from 'vue'
import { DEFAULT_THEME_ID, THEME_OPTIONS } from '../constants/themes'
import {
  APP_FONT_OPTIONS,
  CODE_FONT_OPTIONS,
  DEFAULT_APP_FONT_ID,
  DEFAULT_CODE_FONT_ID,
} from '../constants/fonts'

const DEFAULT_MODELS = [
  'google/gemini-3-flash-preview',
  'google/gemini-2.5-flash',
  'google/gemini-2.5-flash-lite',
  'openrouter/free',
]

export const usePreferencesStore = defineStore('preferences', () => {
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
  }
})
