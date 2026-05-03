<template>
  <section class="scrollbar-hidden relative h-full overflow-y-auto">
    <div class="scrollbar-hidden h-full overflow-y-auto pb-24">
      <h2 class="mb-4 text-lg font-bold text-[var(--color-text-main)]">LLM &amp; API Keys</h2>

      <div class="space-y-5">
        <div class="space-y-2">
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
        </div>

        <div class="border-t border-[var(--color-border)]"></div>

        <div class="space-y-3">
          <label class="mb-1.5 block section-label">
            {{ provider === 'ollama' ? 'Ollama base URL' : apiKeyLabel }}
          </label>

          <div v-if="provider === 'ollama'" class="space-y-2">
            <input
              v-model="ollamaBaseUrl"
              type="text"
              class="input-base"
              placeholder="http://localhost:11434"
            />
          </div>

          <div v-else class="space-y-2">
            <div class="relative">
              <input
                :value="apiKey"
                :type="showKey ? 'text' : 'password'"
                class="input-base pr-10"
                :placeholder="apiKeyPlaceholder"
                @input="setApiKey($event.target.value)"
              />
              <button
                type="button"
                class="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-[var(--color-text-muted)] hover:bg-[var(--color-base-muted)] hover:text-[var(--color-text-main)]"
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

            <div class="flex items-center gap-2">
              <button
                type="button"
                class="btn-secondary px-3 py-2 text-xs"
                :disabled="verifyLoading || saveLoading || deleteLoading"
                @click="handleVerifyAndSaveKey"
              >
                <span v-if="verifyLoading" class="inline-flex items-center gap-2">
                  <span class="h-3 w-3 animate-spin rounded-full border-2 border-[var(--color-accent)]/40 border-t-[var(--color-accent)]"></span>
                  Verifying...
                </span>
                <span v-else>Verify &amp; save key</span>
              </button>
              <button
                v-if="selectedProviderApiKeyPresent"
                type="button"
                class="btn-secondary px-3 py-2 text-xs"
                :disabled="verifyLoading || saveLoading || deleteLoading"
                @click="handleDeleteSavedKey"
              >
                <span v-if="deleteLoading" class="inline-flex items-center gap-2">
                  <span class="h-3 w-3 animate-spin rounded-full border-2 border-[var(--color-accent)]/40 border-t-[var(--color-accent)]"></span>
                  Removing...
                </span>
                <span v-else>Delete saved key</span>
              </button>
              <span v-if="verifySuccessMessage" class="text-xs text-[var(--color-success)]">✓ {{ verifySuccessMessage }}</span>
            </div>

            <p v-if="verifyError" class="text-xs text-[var(--color-danger)]">{{ verifyError }}</p>
            <p v-if="providerApiKeyPortal" class="text-xs text-[var(--color-text-muted)]">
              Need an API key?
              <a
                :href="providerApiKeyPortal"
                target="_blank"
                rel="noopener noreferrer"
                class="font-medium text-[var(--color-accent)] hover:underline"
                @click.prevent="openProviderApiKeyPortal"
              >
                Create {{ providerDisplayName }} API key
              </a>
            </p>
          </div>

          <p v-if="refreshNotice" class="text-xs text-[var(--color-info)]">{{ refreshNotice }}</p>
        </div>

        <div class="border-t border-[var(--color-border)]"></div>

        <div class="space-y-3">
          <div class="grid grid-cols-2 gap-3">
            <div class="space-y-2">
              <label class="mb-1.5 block section-label">Main model</label>
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
            </div>

            <div class="space-y-2">
              <label class="mb-1.5 block section-label">
                Lite model
                <span class="normal-case tracking-normal font-normal text-xs text-[var(--color-text-muted)]">for quick tasks</span>
              </label>
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
            </div>
          </div>

          <div class="mt-4 flex items-center justify-between rounded-lg border border-[var(--color-border)] bg-[var(--color-base-soft)]/40 px-3 py-2">
            <label v-if="provider !== 'ollama'" class="inline-flex cursor-pointer items-center gap-2 text-xs text-[var(--color-text-sub)]">
              <input v-model="showAllModels" type="checkbox" class="rounded border-[var(--color-border-strong)]" />
              Show all models
            </label>
            <p v-else class="text-xs text-[var(--color-text-muted)]">Ollama shows local models.</p>

            <button
              type="button"
              class="inline-flex h-8 w-8 items-center justify-center rounded-md border border-[var(--color-border-strong)] text-[var(--color-accent)] transition-colors hover:bg-[var(--color-base)] disabled:cursor-not-allowed disabled:opacity-60"
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
        </div>

        <div class="border-t border-[var(--color-border)]"></div>

        <div class="space-y-3">
          <div class="rounded-xl border border-[var(--color-border)] bg-[var(--color-base-soft)]/40 px-3 py-3">
            <label class="flex cursor-pointer items-start gap-3">
              <input
                v-model="allowLlmDataSamples"
                type="checkbox"
                class="mt-1 rounded border-[var(--color-border-strong)]"
              />
              <span class="min-w-0">
                <span class="block text-sm font-medium text-[var(--color-text-main)]">
                  Allow bounded data samples in LLM prompts
                </span>
                <span class="mt-1 block text-xs leading-relaxed text-[var(--color-text-muted)]">
                  Off keeps row previews local. On allows small table samples and result previews to be sent to your selected LLM provider, and enables insight-first result explanations.
                </span>
              </span>
            </label>
          </div>
        </div>

        <div class="border-t border-[var(--color-border)]"></div>

        <div class="space-y-3">
          <button
            type="button"
            class="inline-flex items-center gap-2 text-xs text-[var(--color-text-muted)]"
            @click="showAdvanced = !showAdvanced"
          >
            <span>{{ showAdvanced ? '▾' : '▸' }}</span>
            <span>Advanced settings</span>
          </button>

          <div
            class="overflow-hidden transition-all duration-200 ease-in-out"
            :style="{ maxHeight: showAdvanced ? '620px' : '0px' }"
          >
            <div class="grid grid-cols-2 gap-3 pt-1">
              <label class="space-y-1">
                <span class="block text-xs text-[var(--color-text-sub)]">Slow-request warning (seconds)</span>
                <input
                  v-model.number="slowRequestWarningSeconds"
                  type="number"
                  min="5"
                  max="600"
                  step="5"
                  class="input-base"
                />
              </label>

              <label class="space-y-1">
                <span class="block text-xs text-[var(--color-text-sub)]">Max tokens</span>
                <input
                  v-model.number="llmMaxTokens"
                  type="number"
                  min="1"
                  step="1"
                  class="input-base"
                />
              </label>

              <label v-if="advancedFields.topK" class="space-y-1">
                <span class="block text-xs text-[var(--color-text-sub)]">Top K</span>
                <input
                  v-model.number="llmTopK"
                  type="number"
                  min="0"
                  step="1"
                  class="input-base"
                />
              </label>

              <label v-if="advancedFields.temperature" class="space-y-1">
                <div class="flex items-center justify-between">
                  <span class="block text-xs text-[var(--color-text-sub)]">Temperature</span>
                  <span class="text-xs text-[var(--color-text-muted)]">{{ llmTemperature.toFixed(1) }}</span>
                </div>
                <input v-model.number="llmTemperature" type="range" min="0" max="2" step="0.1" class="w-full accent-[var(--color-accent)]" />
              </label>

              <label v-if="advancedFields.topP" class="space-y-1">
                <div class="flex items-center justify-between">
                  <span class="block text-xs text-[var(--color-text-sub)]">Top P</span>
                  <span class="text-xs text-[var(--color-text-muted)]">{{ llmTopP.toFixed(2) }}</span>
                </div>
                <input v-model.number="llmTopP" type="range" min="0" max="1" step="0.05" class="w-full accent-[var(--color-accent)]" />
              </label>

              <label v-if="advancedFields.frequencyPenalty" class="space-y-1">
                <div class="flex items-center justify-between">
                  <span class="block text-xs text-[var(--color-text-sub)]">Frequency penalty</span>
                  <span class="text-xs text-[var(--color-text-muted)]">{{ llmFrequencyPenalty.toFixed(1) }}</span>
                </div>
                <input v-model.number="llmFrequencyPenalty" type="range" min="0" max="2" step="0.1" class="w-full accent-[var(--color-accent)]" />
              </label>

              <label v-if="advancedFields.presencePenalty" class="space-y-1">
                <div class="flex items-center justify-between">
                  <span class="block text-xs text-[var(--color-text-sub)]">Presence penalty</span>
                  <span class="text-xs text-[var(--color-text-muted)]">{{ llmPresencePenalty.toFixed(1) }}</span>
                </div>
                <input v-model.number="llmPresencePenalty" type="range" min="0" max="2" step="0.1" class="w-full accent-[var(--color-accent)]" />
              </label>
            </div>
            <div class="pt-2">
              <button type="button" class="text-xs text-[var(--color-accent)] hover:underline" @click="resetAdvancedDefaults">
                Reset to defaults
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="absolute inset-x-0 bottom-0 flex justify-end gap-2 border-t border-[var(--color-border)] bg-[var(--color-base)] px-1 pt-4">
      <button
        type="button"
        class="btn-secondary px-4 py-2 text-sm"
        @click="emit('close-request')"
      >
        Cancel
      </button>
      <button
        type="button"
        class="btn-primary px-4 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-60"
        :disabled="saveLoading"
        @click="saveConfiguration"
      >
        <span v-if="saveLoading" class="inline-flex items-center gap-2">
          <span class="h-3 w-3 animate-spin rounded-full border-2 border-white/60 border-t-white"></span>
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
  getModelMeta,
  setMainModel,
  clearTransientMessages,
  resetForAuthBoundary,
} = llm

const showKey = ref(false)
const showAdvanced = ref(false)
const deleteLoading = ref(false)

const providerOptions = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'openrouter', label: 'OpenRouter' },
  { value: 'ollama', label: 'Ollama (local)' },
]

const verifySuccessMessage = computed(() => String(verifySuccess.value || '').trim())
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
})

watch(
  () => authStore.userId,
  async (newUserId, oldUserId) => {
    if (!newUserId || newUserId === oldUserId) return
    showKey.value = false
    resetForAuthBoundary()
    try {
      await loadPreferences(null, false)
    } catch (_error) {
      toast.error('Provider Error', 'Could not load provider configuration.')
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
</style>
