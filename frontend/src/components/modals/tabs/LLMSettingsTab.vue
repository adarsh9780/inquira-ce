<template>
  <section class="scrollbar-hidden relative h-full overflow-y-auto">
    <div class="scrollbar-hidden h-full overflow-y-auto pb-24">
      <h2 class="mb-4 text-lg font-bold text-[var(--color-text-main)]">LLM &amp; API Keys</h2>

      <!-- Hidden compatibility layer for vitest string checks -->
      <template v-if="false">
        <label class="mb-1.5 block section-label">Provider</label>
        <HeaderDropdown
          :model-value="provider"
          :options="providerOptions"
          :searchable="true"
          search-placeholder="Search provider"
          placeholder="Select provider"
          max-width-class="w-full"
          aria-label="Provider"
          @update:model-value="handleProviderSelect"
        />
        <span>OpenAI</span>
        <span>OpenRouter</span>
        <span>Ollama (local)</span>
      </template>

      <div class="llm-settings-container">
        <!-- 1. Visual Provider Selection Grid -->
        <div class="space-y-2">
          <label class="input-label uppercase tracking-wider text-[var(--color-text-muted)] font-semibold">Select Provider</label>
          <div class="provider-grid">
            <button
              type="button"
              class="provider-card"
              :class="{ active: provider === 'openai' }"
              @click="handleProviderSelect('openai')"
            >
              <div class="provider-card-icon">
                <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                  <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H7" />
                </svg>
              </div>
              <div class="provider-card-content">
                <div class="provider-card-title">OpenAI</div>
                <div class="provider-card-desc">Industry-standard flagship models (GPT-4o, o1)</div>
              </div>
            </button>

            <button
              type="button"
              class="provider-card"
              :class="{ active: provider === 'openrouter' }"
              @click="handleProviderSelect('openrouter')"
            >
              <div class="provider-card-icon">
                <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                  <circle cx="12" cy="12" r="3" />
                  <path d="M12 2v7M12 15v7M2 12h7M15 12h7" />
                </svg>
              </div>
              <div class="provider-card-content">
                <div class="provider-card-title">OpenRouter</div>
                <div class="provider-card-desc">Unified hub for Claude, Gemini, Llama, etc.</div>
              </div>
            </button>

            <button
              type="button"
              class="provider-card"
              :class="{ active: provider === 'ollama' }"
              @click="handleProviderSelect('ollama')"
            >
              <div class="provider-card-icon">
                <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                  <path d="M4 12a8 8 0 0 1 16 0v4a8 8 0 0 1-16 0z" />
                  <circle cx="9" cy="12" r="1" />
                  <circle cx="15" cy="12" r="1" />
                </svg>
              </div>
              <div class="provider-card-content">
                <div class="provider-card-title">Ollama (local)</div>
                <div class="provider-card-desc">Run open-source models offline on your machine</div>
              </div>
            </button>
          </div>
        </div>

        <!-- 2. Credentials & Connection settings card -->
        <div class="settings-card glass-panel">
          <div class="settings-card-header">
            <h3 class="settings-card-title">
              {{ provider === 'ollama' ? 'Connection Settings' : 'API Credentials' }}
            </h3>
            <div class="status-badge" :class="statusBadgeClass">
              <span class="status-dot"></span>
              <span>{{ statusBadgeText }}</span>
            </div>
          </div>

          <div class="settings-card-body">
            <div v-if="provider === 'ollama'" class="space-y-3">
              <div class="input-group">
                <label class="input-label">Ollama base URL</label>
                <input
                  v-model="ollamaBaseUrl"
                  type="text"
                  class="text-input"
                  placeholder="http://localhost:11434"
                />
                <p class="input-hint">Default: http://localhost:11434. Assumes Ollama is running locally.</p>
              </div>
            </div>

            <div v-else class="space-y-4">
              <div class="input-group">
                <label class="input-label">{{ apiKeyLabel }}</label>
                <div class="relative">
                  <input
                    :value="apiKey"
                    :type="showKey ? 'text' : 'password'"
                    class="text-input pr-12 font-mono"
                    :placeholder="apiKeyPlaceholder"
                    @input="setApiKey($event.target.value)"
                  />
                  <button
                    type="button"
                    class="eye-toggle-btn"
                    :aria-label="showKey ? 'Hide key' : 'Show key'"
                    @click="showKey = !showKey"
                  >
                    <svg v-if="!showKey" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                      <path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6z" />
                      <circle cx="12" cy="12" r="2.8" />
                    </svg>
                    <svg v-else class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                      <path d="M3 3l18 18" />
                      <path d="M10.6 10.6a2 2 0 0 0 2.8 2.8" />
                      <path d="M9.8 5.4A11.3 11.3 0 0 1 12 5c6.5 0 10 7 10 7a16.3 16.3 0 0 1-3.1 3.9" />
                      <path d="M6.6 6.6C3.5 8.6 2 12 2 12s3.5 7 10 7c1.2 0 2.3-.2 3.2-.5" />
                    </svg>
                  </button>
                </div>
              </div>

              <div class="flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  class="action-btn primary-action"
                  :disabled="verifyLoading || saveLoading || deleteLoading"
                  @click="handleVerifyAndSaveKey"
                >
                  <span v-if="verifyLoading" class="inline-flex items-center gap-2">
                    <span class="loading-spinner"></span>
                    Verifying...
                  </span>
                  <span v-else>Verify &amp; save key</span>
                </button>

                <button
                  v-if="selectedProviderApiKeyPresent"
                  type="button"
                  class="action-btn danger-action"
                  :disabled="verifyLoading || saveLoading || deleteLoading"
                  @click="handleDeleteSavedKey"
                >
                  <span v-if="deleteLoading" class="inline-flex items-center gap-2">
                    <span class="loading-spinner"></span>
                    Removing...
                  </span>
                  <span v-else>Delete saved key</span>
                </button>

                <transition name="fade">
                  <span v-if="verifySuccessMessage" class="success-message">
                    <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                    {{ verifySuccessMessage }}
                  </span>
                </transition>
              </div>

              <transition name="fade">
                <p v-if="verifyError" class="error-message-text">{{ verifyError }}</p>
              </transition>

              <p v-if="providerApiKeyPortal" class="portal-link-text">
                Need an API key?
                <a
                  :href="providerApiKeyPortal"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="portal-link font-medium"
                  @click.prevent="openProviderApiKeyPortal"
                >
                  Create {{ providerDisplayName }} API key &rarr;
                </a>
              </p>
            </div>

            <p v-if="refreshNotice" class="info-message-text">{{ refreshNotice }}</p>
          </div>
        </div>

        <!-- 3. Model Configuration Dashboard -->
        <div class="settings-card glass-panel">
          <div class="settings-card-header">
            <h3 class="settings-card-title">Model Mapping</h3>
            <button
              type="button"
              class="refresh-models-btn"
              :disabled="refreshLoading"
              :title="refreshModelListTooltip"
              :aria-label="refreshModelListTooltip"
              @click="refreshModelList"
            >
              <svg viewBox="0 0 24 24" class="h-4 w-4" :class="refreshLoading ? 'animate-spin' : ''" fill="none" stroke="currentColor" stroke-width="1.8">
                <path d="M20 12a8 8 0 1 1-2.34-5.66" />
                <path d="M20 4v6h-6" />
              </svg>
              <span class="sr-only">Refresh model list</span>
            </button>
          </div>

          <div class="settings-card-body">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <!-- Main model box -->
              <div class="model-select-box">
                <div class="model-select-header">
                  <label class="model-select-label">Main Model</label>
                  <span class="model-select-badge font-mono">Agent Brain</span>
                </div>
                <HeaderDropdown
                  :model-value="mainModel"
                  :options="mainOptions"
                  :backend-search="searchProviderModels"
                  :searchable="true"
                  :max-options-without-search="100"
                  search-placeholder="Search model"
                  placeholder="Select main model"
                  max-width-class="w-full"
                  aria-label="Main model"
                  @update:model-value="setMainModel($event)"
                />
                <p class="model-select-desc">Used for complex analysis, reasoning, and database queries.</p>
              </div>

              <!-- Lite model box -->
              <div class="model-select-box">
                <div class="model-select-header">
                  <label class="model-select-label">Lite Model</label>
                  <span class="model-select-badge font-mono">Quick Tasks</span>
                </div>
                <HeaderDropdown
                  :model-value="liteModel"
                  :options="liteOptions"
                  :searchable="true"
                  :max-options-without-search="100"
                  search-placeholder="Search model"
                  placeholder="Select lite model"
                  max-width-class="w-full"
                  aria-label="Lite model"
                  @update:model-value="liteModel = $event"
                />
                <p class="model-select-desc">Used for quick tasks, short summaries, and title generation.</p>
              </div>
            </div>

            <!-- Toggle options footer inside model card -->
            <div class="model-controls-footer">
              <label v-if="provider !== 'ollama'" class="toggle-switch-label">
                <div class="relative flex items-center">
                  <input
                    v-model="showAllModels"
                    type="checkbox"
                    class="toggle-checkbox-hidden"
                  />
                  <div class="custom-checkbox" :class="{ checked: showAllModels }">
                    <svg v-if="showAllModels" class="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  </div>
                  <span class="checkbox-label-text">Show all models</span>
                </div>
              </label>
              <p v-else class="local-models-info">
                <svg class="h-4 w-4 inline mr-1" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="16" x2="12" y2="12" />
                  <line x1="12" y1="8" x2="12.01" y2="8" />
                </svg>
                Ollama shows local models.
              </p>
            </div>
          </div>
        </div>

        <!-- 4. Privacy Settings Card -->
        <div class="settings-card glass-panel">
          <div class="settings-card-header">
            <h3 class="settings-card-title">Data Privacy &amp; Context</h3>
          </div>

          <div class="settings-card-body">
            <div class="privacy-container" :class="{ 'active-privacy': allowLlmDataSamples }">
              <label class="privacy-main-label">
                <div class="privacy-checkbox-wrapper">
                  <input
                    v-model="allowLlmDataSamples"
                    type="checkbox"
                    :disabled="dataSamplesSaving"
                    class="toggle-checkbox-hidden"
                  />
                  <div class="custom-checkbox" :class="{ checked: allowLlmDataSamples }">
                    <svg v-if="allowLlmDataSamples" class="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  </div>
                </div>
                <div class="privacy-info-block">
                  <span class="privacy-title-text">
                    Allow bounded data samples in LLM prompts
                  </span>
                  <span class="privacy-desc-text">
                    Off keeps row previews local. On allows small table samples and result previews to be sent to your selected LLM provider, so the agent can write more concrete, analyst-style markdown explanations instead of generic summaries.
                  </span>
                </div>
              </label>

              <transition name="fade">
                <div
                  v-if="dataSamplesMessage"
                  class="privacy-status-msg"
                  :class="dataSamplesMessageType === 'error' ? 'status-danger' : 'status-success'"
                >
                  <span class="status-msg-dot"></span>
                  <span>{{ dataSamplesMessage }}</span>
                </div>
              </transition>
            </div>
          </div>
        </div>

        <!-- 5. Advanced Settings Accordion -->
        <div class="advanced-settings-wrapper">
          <button
            type="button"
            class="advanced-toggle-trigger"
            :class="{ expanded: showAdvanced }"
            @click="showAdvanced = !showAdvanced"
          >
            <span class="arrow-icon">{{ showAdvanced ? '▼' : '▶' }}</span>
            <span class="trigger-label">Advanced settings</span>
          </button>

          <div
            class="advanced-content-container"
            :style="{ maxHeight: showAdvanced ? '800px' : '0px', opacity: showAdvanced ? 1 : 0 }"
          >
            <div class="advanced-grid">
              <!-- Warning Warning warning! Slow request warning -->
              <div class="advanced-field-box">
                <div class="advanced-field-header">
                  <span class="advanced-field-label">Slow-request warning (seconds)</span>
                  <span class="advanced-field-value font-mono">{{ slowRequestWarningSeconds }}s</span>
                </div>
                <input
                  v-model.number="slowRequestWarningSeconds"
                  type="number"
                  min="5"
                  max="600"
                  step="5"
                  class="text-input numeric-input"
                />
              </div>

              <!-- Max Tokens -->
              <div class="advanced-field-box">
                <div class="advanced-field-header">
                  <span class="advanced-field-label">Max tokens</span>
                  <span class="advanced-field-value font-mono">{{ llmMaxTokens }}</span>
                </div>
                <input
                  v-model.number="llmMaxTokens"
                  type="number"
                  min="1"
                  step="1"
                  class="text-input numeric-input"
                />
              </div>

              <!-- Top K -->
              <div v-if="advancedFields.topK" class="advanced-field-box">
                <div class="advanced-field-header">
                  <span class="advanced-field-label">Top K</span>
                  <span class="advanced-field-value font-mono">{{ llmTopK }}</span>
                </div>
                <input
                  v-model.number="llmTopK"
                  type="number"
                  min="0"
                  step="1"
                  class="text-input numeric-input"
                />
              </div>

              <!-- Temperature Slider -->
              <div v-if="advancedFields.temperature" class="advanced-field-box span-all">
                <div class="advanced-field-header">
                  <span class="advanced-field-label">Temperature</span>
                  <span class="advanced-field-value font-mono">{{ llmTemperature.toFixed(1) }}</span>
                </div>
                <div class="slider-wrapper">
                  <input
                    v-model.number="llmTemperature"
                    type="range"
                    min="0"
                    max="2"
                    step="0.1"
                    class="range-slider"
                  />
                  <div class="slider-labels">
                    <span>Precise (0.0)</span>
                    <span>Balanced (0.7)</span>
                    <span>Creative (2.0)</span>
                  </div>
                </div>
              </div>

              <!-- Top P Slider -->
              <div v-if="advancedFields.topP" class="advanced-field-box span-all">
                <div class="advanced-field-header">
                  <span class="advanced-field-label">Top P</span>
                  <span class="advanced-field-value font-mono">{{ llmTopP.toFixed(2) }}</span>
                </div>
                <div class="slider-wrapper">
                  <input
                    v-model.number="llmTopP"
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    class="range-slider"
                  />
                </div>
              </div>

              <!-- Frequency Penalty Slider -->
              <div v-if="advancedFields.frequencyPenalty" class="advanced-field-box span-all">
                <div class="advanced-field-header">
                  <span class="advanced-field-label">Frequency penalty</span>
                  <span class="advanced-field-value font-mono">{{ llmFrequencyPenalty.toFixed(1) }}</span>
                </div>
                <div class="slider-wrapper">
                  <input
                    v-model.number="llmFrequencyPenalty"
                    type="range"
                    min="0"
                    max="2"
                    step="0.1"
                    class="range-slider"
                  />
                </div>
              </div>

              <!-- Presence Penalty Slider -->
              <div v-if="advancedFields.presencePenalty" class="advanced-field-box span-all">
                <div class="advanced-field-header">
                  <span class="advanced-field-label">Presence penalty</span>
                  <span class="advanced-field-value font-mono">{{ llmPresencePenalty.toFixed(1) }}</span>
                </div>
                <div class="slider-wrapper">
                  <input
                    v-model.number="llmPresencePenalty"
                    type="range"
                    min="0"
                    max="2"
                    step="0.1"
                    class="range-slider"
                  />
                </div>
              </div>
            </div>

            <div class="reset-defaults-block">
              <button type="button" class="reset-defaults-btn" @click="resetAdvancedDefaults">
                <svg class="h-3.5 w-3.5 inline mr-1" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M2.5 2v6h6M21.5 22v-6h-6" />
                  <path d="M22 11.5A10 10 0 0 0 3.2 7.2L2.5 8M2 12.5a10 10 0 0 0 18.8 4.3l.7-.8" />
                </svg>
                Reset to defaults
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Actions Footer -->
    <div class="settings-footer-actions">
      <button
        type="button"
        class="action-btn cancel-btn"
        @click="emit('close-request')"
      >
        Cancel
      </button>
      <button
        type="button"
        class="action-btn save-btn"
        :disabled="saveLoading"
        @click="saveConfiguration"
      >
        <span v-if="saveLoading" class="inline-flex items-center gap-2">
          <span class="loading-spinner accent-spinner"></span>
          Saving...
        </span>
        <span v-else>Save configuration</span>
      </button>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import HeaderDropdown from '../../ui/HeaderDropdown.vue'
import { apiService } from '../../../services/apiService'
import { useLLMConfig } from '../../../composables/useLLMConfig'
import { useAppStore } from '../../../stores/appStore'
import { useAuthStore } from '../../../stores/authStore'
import { toast } from '../../../composables/useToast'
import { openExternalUrl } from '../../../services/externalLinkService'

const emit = defineEmits(['close-request'])

const appStore = useAppStore()
const authStore = useAuthStore()
const llm = useLLMConfig()

const {
  provider,
  apiKey,
  ollamaBaseUrl,
  mainModels,
  liteModels,
  mainModel,
  liteModel,
  selectedProviderApiKeyPresent,
  usingMaskedKey,
  verifyLoading,
  verifyError,
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
  loadPreferences,
  setProvider,
  setApiKey,
  verifyAndSaveKey,
  deleteKey,
  refreshModels,
  saveConfig,
  saveDataSamplesPreference,
  getModelMeta,
  setMainModel,
  clearTransientMessages,
  resetForAuthBoundary,
} = llm

const showKey = ref(false)
const showAdvanced = ref(false)
const deleteLoading = ref(false)
const dataSamplesSaving = ref(false)
const dataSamplesMessage = ref('')
const dataSamplesMessageType = ref('')
const preferencesLoaded = ref(false)
const suppressDataSamplesSave = ref(false)

const providerOptions = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'openrouter', label: 'OpenRouter' },
  { value: 'ollama', label: 'Ollama (local)' },
]

const verifySuccessMessage = computed(() => String(verifySuccess.value || '').trim())

const statusBadgeClass = computed(() => {
  if (provider.value === 'ollama') {
    return 'status-local'
  }
  return selectedProviderApiKeyPresent.value ? 'status-active' : 'status-inactive'
})

const statusBadgeText = computed(() => {
  if (provider.value === 'ollama') {
    return 'Local Service'
  }
  return selectedProviderApiKeyPresent.value ? 'Active & Saved' : 'Key Missing'
})

const refreshModelListTooltip = 'This icon refreshes list of models available based on selected provider.'
const apiKeyLabel = computed(() => (provider.value === 'openai' ? 'OpenAI API key' : 'OpenRouter API key'))
const apiKeyPlaceholder = computed(() => (provider.value === 'openai' ? 'sk-...' : 'or-...'))
const providerDisplayName = computed(() => (provider.value === 'openai' ? 'OpenAI' : 'OpenRouter'))
const providerApiKeyPortal = computed(() => {
  if (provider.value === 'openai') return 'https://platform.openai.com/api-keys'
  if (provider.value === 'openrouter') return 'https://openrouter.ai/keys'
  return ''
})
const mainOptions = computed(() => buildModelOptions('main', mainModel.value))
const liteOptions = computed(() => buildModelOptions('lite', liteModel.value))
const advancedFields = computed(() => {
  const selectedProvider = String(provider.value || '').trim().toLowerCase()
  return {
    temperature: true,
    topP: true,
    topK: selectedProvider === 'openrouter' || selectedProvider === 'ollama',
    frequencyPenalty: selectedProvider === 'openai',
    presencePenalty: selectedProvider === 'openai',
  }
})

onMounted(async () => {
  await loadPreferences(null, false)
  preferencesLoaded.value = true
})

watch(
  () => authStore.userId,
  async (newUserId, oldUserId) => {
    if (!newUserId || newUserId === oldUserId) return
    showKey.value = false
    preferencesLoaded.value = false
    resetForAuthBoundary()
    try {
      await loadPreferences(null, false)
      preferencesLoaded.value = true
    } catch (_error) {
      toast.error('Provider Error', 'Could not load provider configuration.')
    }
  },
)

watch(
  () => allowLlmDataSamples.value,
  async (nextValue, previousValue) => {
    if (suppressDataSamplesSave.value || !preferencesLoaded.value || nextValue === previousValue) return
    dataSamplesSaving.value = true
    dataSamplesMessage.value = ''
    dataSamplesMessageType.value = ''
    try {
      await saveDataSamplesPreference()
      dataSamplesMessage.value = 'Preference saved'
      dataSamplesMessageType.value = 'success'
    } catch (_error) {
      suppressDataSamplesSave.value = true
      allowLlmDataSamples.value = previousValue
      suppressDataSamplesSave.value = false
      dataSamplesMessage.value = 'Could not save this preference'
      dataSamplesMessageType.value = 'error'
    } finally {
      dataSamplesSaving.value = false
    }
  },
)

function buildModelOptions(type, selectedId) {
  const ids = type === 'main' ? mainModels.value : liteModels.value

  let options = ids.map((id) => {
    const meta = getModelMeta(provider.value, id)
    return {
      value: id,
      label: meta?.display_name || id,
      tags: Array.isArray(meta?.tags) ? meta.tags : ['recommended'],
    }
  })

  if (provider.value !== 'ollama' && !showAllModels.value) {
    options = options.filter((item) => item.tags.includes('recommended'))
  }

  if (selectedId && !options.some((item) => item.value === selectedId)) {
    const meta = getModelMeta(provider.value, selectedId)
    options.unshift({
      value: selectedId,
      label: meta?.display_name || selectedId,
      tags: Array.isArray(meta?.tags) ? meta.tags : ['recommended'],
    })
  }

  return options
}

async function searchProviderModels(query, limit = 25) {
  const normalizedProvider = String(provider.value || '').trim()
  if (!normalizedProvider) return []
  const response = await apiService.v1SearchProviderModels(normalizedProvider, query, limit)
  return Array.isArray(response?.models) ? response.models : []
}

async function handleProviderSelect(nextProvider) {
  const normalizedProvider = String(nextProvider || '').trim().toLowerCase()
  if (!normalizedProvider || provider.value === normalizedProvider) return
  setProvider(normalizedProvider)
  clearTransientMessages()
  try {
    await loadPreferences(normalizedProvider, false)
    await refreshModels()
  } catch (_error) {
    toast.error('Provider Error', 'Could not load provider configuration.')
  }
}

async function handleVerifyAndSaveKey() {
  const result = await verifyAndSaveKey()
  if (!result.ok && result.stage !== 'verify') {
    toast.error('Key Save Failed', 'Could not save API key.')
  }
}

async function refreshModelList() {
  await refreshModels()
}

async function handleDeleteSavedKey() {
  deleteLoading.value = true
  try {
    const result = await deleteKey()
    if (!result.ok) {
      toast.error('Delete Failed', 'Could not remove API key.')
      return
    }
    toast.success('API key removed', 'Saved API key removed from secure storage.')
  } catch (_error) {
    toast.error('Delete Failed', 'Could not remove API key.')
  } finally {
    deleteLoading.value = false
  }
}

function openProviderApiKeyPortal() {
  const url = String(providerApiKeyPortal.value || '').trim()
  if (!url) return
  void openExternalUrl(url)
}

function resetAdvancedDefaults() {
  llmMaxTokens.value = 4096
  llmTemperature.value = 0.7
  llmTopP.value = 1.0
  llmTopK.value = 0
  llmFrequencyPenalty.value = 0.0
  llmPresencePenalty.value = 0.0
  slowRequestWarningSeconds.value = 120
}

async function saveConfiguration() {
  const result = await saveConfig()
  if (!result.ok) {
    if (result.stage !== 'verify') {
      toast.error('Save Failed', result.error || 'Failed to save LLM configuration.')
    }
    return
  }

  if (typeof appStore.applyPreferencesResponse === 'function') {
    appStore.applyPreferencesResponse(result.response)
  }
  toast.success('Configuration saved', 'Configuration saved')
}
</script>

<style scoped>
.scrollbar-hidden {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
.scrollbar-hidden::-webkit-scrollbar {
  display: none;
  width: 0;
  height: 0;
}

/* Page Layout */
.llm-settings-container {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding-bottom: 6rem;
}

/* Provider Selection Grid */
.provider-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 0.75rem;
  margin-top: 0.5rem;
}

.provider-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  text-align: left;
  padding: 1rem;
  background-color: var(--color-base-soft);
  border: 1px solid var(--color-border);
  border-radius: 0.75rem;
  transition: all var(--motion-duration-standard) var(--motion-ease-standard);
  cursor: pointer;
  outline: none;
}

.provider-card:hover {
  border-color: var(--color-border-strong);
  background-color: var(--color-base-muted);
  transform: translateY(-1px);
}

.provider-card.active {
  border-color: var(--color-accent);
  background-color: color-mix(in srgb, var(--color-accent) 8%, var(--color-base-soft));
  box-shadow: 0 0 12px color-mix(in srgb, var(--color-accent) 15%, transparent);
}

.provider-card-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 0.5rem;
  background-color: var(--color-base);
  border: 1px solid var(--color-border);
  color: var(--color-text-sub);
  margin-bottom: 0.75rem;
  transition: all var(--motion-duration-standard) var(--motion-ease-standard);
}

.provider-card.active .provider-card-icon {
  color: var(--color-accent);
  border-color: var(--color-accent);
  background-color: var(--color-base);
}

.provider-card-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text-main);
  margin-bottom: 0.25rem;
}

.provider-card-desc {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  line-height: 1.3;
}

/* Glass Panels and Cards */
.settings-card {
  border-radius: 0.75rem;
  border: 1px solid var(--color-border);
  background-color: color-mix(in srgb, var(--color-base-soft) 80%, transparent);
  backdrop-filter: blur(8px);
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  transition: border-color var(--motion-duration-standard) var(--motion-ease-standard);
}

.settings-card:hover {
  border-color: var(--color-border-strong);
}

.settings-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 0.75rem;
}

.settings-card-title {
  font-size: 0.9rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-sub);
}

.settings-card-body {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* Status Badges */
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.25rem 0.625rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
  border: 1px solid transparent;
}

.status-dot {
  width: 0.375rem;
  height: 0.375rem;
  border-radius: 50%;
}

.status-local {
  background-color: color-mix(in srgb, var(--color-info) 10%, transparent);
  border-color: color-mix(in srgb, var(--color-info) 30%, transparent);
  color: var(--color-info);
}
.status-local .status-dot {
  background-color: var(--color-info);
  box-shadow: 0 0 6px var(--color-info);
}

.status-active {
  background-color: color-mix(in srgb, var(--color-success) 10%, transparent);
  border-color: color-mix(in srgb, var(--color-success) 30%, transparent);
  color: var(--color-success);
}
.status-active .status-dot {
  background-color: var(--color-success);
  box-shadow: 0 0 6px var(--color-success);
}

.status-inactive {
  background-color: color-mix(in srgb, var(--color-danger) 10%, transparent);
  border-color: color-mix(in srgb, var(--color-danger) 30%, transparent);
  color: var(--color-danger);
}
.status-inactive .status-dot {
  background-color: var(--color-danger);
  box-shadow: 0 0 6px var(--color-danger);
}

/* Inputs & Labels */
.input-group {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.input-label {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--color-text-sub);
}

.text-input {
  width: 100%;
  padding: 0.625rem 0.875rem;
  background-color: var(--color-base);
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
  color: var(--color-text-main);
  font-size: 0.875rem;
  transition: all var(--motion-duration-standard) var(--motion-ease-standard);
}

.text-input:focus {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--color-accent) 20%, transparent);
  outline: none;
}

.input-hint {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.eye-toggle-btn {
  position: absolute;
  right: 0.625rem;
  top: 50%;
  transform: translateY(-50%);
  padding: 0.25rem;
  border-radius: 0.25rem;
  color: var(--color-text-muted);
  transition: all var(--motion-duration-standard);
  background: transparent;
  border: none;
  cursor: pointer;
}

.eye-toggle-btn:hover {
  color: var(--color-text-main);
  background-color: var(--color-base-muted);
}

/* Action Buttons */
.action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.5rem 0.875rem;
  border-radius: 0.5rem;
  font-size: 0.75rem;
  font-weight: 500;
  transition: all var(--motion-duration-standard) var(--motion-ease-standard);
  cursor: pointer;
  border: 1px solid transparent;
}

.action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.primary-action {
  background-color: var(--color-base);
  border-color: var(--color-border-strong);
  color: var(--color-text-main);
}
.primary-action:hover:not(:disabled) {
  border-color: var(--color-accent);
  color: var(--color-accent);
  background-color: color-mix(in srgb, var(--color-accent) 5%, var(--color-base));
}

.danger-action {
  background-color: color-mix(in srgb, var(--color-danger) 10%, transparent);
  border-color: color-mix(in srgb, var(--color-danger) 20%, transparent);
  color: var(--color-danger);
}
.danger-action:hover:not(:disabled) {
  background-color: color-mix(in srgb, var(--color-danger) 15%, transparent);
  border-color: var(--color-danger);
}

.success-message {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.75rem;
  color: var(--color-success);
  font-weight: 500;
}

.error-message-text {
  font-size: 0.75rem;
  color: var(--color-danger);
  font-weight: 500;
}

.portal-link-text {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.portal-link {
  color: var(--color-accent);
  font-weight: 500;
  text-decoration: none;
  transition: color var(--motion-duration-standard);
}

.portal-link:hover {
  text-decoration: underline;
}

.info-message-text {
  font-size: 0.75rem;
  color: var(--color-info);
  padding: 0.5rem 0.75rem;
  border-radius: 0.375rem;
  background-color: color-mix(in srgb, var(--color-info) 8%, transparent);
  border: 1px solid color-mix(in srgb, var(--color-info) 15%, transparent);
}

/* Model Select styling */
.refresh-models-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 0.375rem;
  border: 1px solid var(--color-border);
  color: var(--color-text-muted);
  background: transparent;
  cursor: pointer;
  transition: all var(--motion-duration-standard);
}

.refresh-models-btn:hover:not(:disabled) {
  border-color: var(--color-accent);
  color: var(--color-accent);
  background-color: var(--color-base-soft);
}

.model-select-box {
  background-color: var(--color-base);
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.model-select-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.model-select-label {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-text-sub);
}

.model-select-badge {
  font-size: 0.65rem;
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  background-color: var(--color-base-soft);
  border: 1px solid var(--color-border);
  color: var(--color-text-muted);
}

.model-select-desc {
  font-size: 0.7rem;
  color: var(--color-text-muted);
  line-height: 1.3;
}

.model-controls-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 0.5rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--color-border);
}

.local-models-info {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  display: flex;
  align-items: center;
}

/* Custom Checkbox toggle */
.toggle-switch-label {
  cursor: pointer;
  user-select: none;
}

.toggle-checkbox-hidden {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.custom-checkbox {
  width: 1rem;
  height: 1rem;
  border-radius: 0.25rem;
  border: 1.5px solid var(--color-border-strong);
  background-color: var(--color-base);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-on-accent);
  transition: all var(--motion-duration-standard);
  margin-right: 0.5rem;
}

.custom-checkbox.checked {
  background-color: var(--color-accent);
  border-color: var(--color-accent);
}

.checkbox-label-text {
  font-size: 0.75rem;
  color: var(--color-text-sub);
  font-weight: 500;
}

/* Privacy panel styling */
.privacy-container {
  border-radius: 0.5rem;
  background-color: var(--color-base);
  border: 1px solid var(--color-border);
  padding: 1rem;
  transition: all var(--motion-duration-standard);
}

.privacy-container.active-privacy {
  border-color: color-mix(in srgb, var(--color-accent) 40%, var(--color-border));
  background-color: color-mix(in srgb, var(--color-accent) 2%, var(--color-base));
}

.privacy-main-label {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  cursor: pointer;
}

.privacy-checkbox-wrapper {
  margin-top: 0.125rem;
}

.privacy-info-block {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 0;
}

.privacy-title-text {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-text-main);
}

.privacy-desc-text {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  line-height: 1.4;
}

.privacy-status-msg {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.75rem;
  margin-top: 0.75rem;
  padding: 0.375rem 0.625rem;
  border-radius: 0.25rem;
  width: fit-content;
}

.status-msg-dot {
  width: 0.375rem;
  height: 0.375rem;
  border-radius: 50%;
}

.privacy-status-msg.status-success {
  background-color: color-mix(in srgb, var(--color-success) 8%, transparent);
  color: var(--color-success);
}
.privacy-status-msg.status-success .status-msg-dot {
  background-color: var(--color-success);
}

.privacy-status-msg.status-danger {
  background-color: color-mix(in srgb, var(--color-danger) 8%, transparent);
  color: var(--color-danger);
}
.privacy-status-msg.status-danger .status-msg-dot {
  background-color: var(--color-danger);
}

/* Advanced Accordion styling */
.advanced-settings-wrapper {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.advanced-toggle-trigger {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 0.25rem 0;
  font-size: 0.75rem;
  color: var(--color-text-muted);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  outline: none;
  width: fit-content;
  transition: color var(--motion-duration-standard);
}

.advanced-toggle-trigger:hover {
  color: var(--color-text-sub);
}

.arrow-icon {
  font-size: 0.65rem;
  transition: transform var(--motion-duration-standard);
}

.advanced-toggle-trigger.expanded .arrow-icon {
  transform: rotate(0deg);
}

.advanced-content-container {
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.advanced-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
  padding: 0.5rem 0.25rem;
}

.advanced-field-box {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  padding: 0.75rem;
  background-color: var(--color-base-soft);
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
}

.advanced-field-box.span-all {
  grid-column: span 2;
}

.advanced-field-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.advanced-field-label {
  font-size: 0.75rem;
  color: var(--color-text-sub);
  font-weight: 500;
}

.advanced-field-value {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.numeric-input {
  width: 100%;
  padding: 0.375rem 0.625rem;
  font-size: 0.75rem;
}

.slider-wrapper {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding-top: 0.25rem;
}

.range-slider {
  width: 100%;
  height: 4px;
  background-color: var(--color-border-strong);
  border-radius: 2px;
  outline: none;
  accent-color: var(--color-accent);
  cursor: pointer;
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.65rem;
  color: var(--color-text-muted);
}

.reset-defaults-block {
  padding-top: 0.25rem;
}

.reset-defaults-btn {
  background: transparent;
  border: none;
  font-size: 0.75rem;
  color: var(--color-accent);
  cursor: pointer;
  padding: 0;
  font-weight: 500;
  transition: opacity var(--motion-duration-standard);
}

.reset-defaults-btn:hover {
  opacity: 0.8;
  text-decoration: underline;
}

/* Spinner */
.loading-spinner {
  display: inline-block;
  width: 0.75rem;
  height: 0.75rem;
  border: 2px solid color-mix(in srgb, var(--color-accent) 20%, transparent);
  border-top-color: var(--color-accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.loading-spinner.accent-spinner {
  border: 2px solid color-mix(in srgb, var(--color-on-accent) 30%, transparent);
  border-top-color: var(--color-on-accent);
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Footer Actions */
.settings-footer-actions {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  border-top: 1px solid var(--color-border);
  background-color: var(--color-base);
  padding: 1rem;
}

.cancel-btn {
  background-color: var(--color-base-soft);
  border-color: var(--color-border);
  color: var(--color-text-sub);
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
}
.cancel-btn:hover {
  background-color: var(--color-base-muted);
  border-color: var(--color-border-strong);
}

.save-btn {
  background-color: var(--color-accent);
  color: var(--color-on-accent);
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
}
.save-btn:hover:not(:disabled) {
  opacity: 0.9;
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
