<template>
  <section class="space-y-4">
    <h2 class="text-lg font-bold text-[var(--color-text-main)]">LLM &amp; API Keys</h2>

    <div class="space-y-3">
      <div class="rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base)]">
        <template v-if="activePanel !== 1 && provider">
          <div class="flex items-center justify-between px-4 py-3">
            <div>
              <p class="text-sm font-medium text-[var(--color-text-main)]">Provider</p>
              <p class="text-xs text-[var(--color-text-sub)]">{{ providerLabel }}</p>
            </div>
            <button
              type="button"
              class="text-xs font-medium text-[var(--color-accent)] hover:brightness-90"
              @click="openPanel(1)"
            >
              Edit
            </button>
          </div>
        </template>

        <div
          class="overflow-hidden transition-all duration-300"
          :class="activePanel === 1 ? 'max-h-[32rem] opacity-100' : 'max-h-0 opacity-0'"
        >
          <div class="space-y-3 px-4 pb-4 pt-2">
            <label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-[var(--color-text-sub)]">Choose provider</label>
            <div class="grid grid-cols-3 gap-3">
              <button
                v-for="card in providerCards"
                :key="card.id"
                type="button"
                class="rounded-lg border px-3 py-3 text-left transition-all"
                :class="provider === card.id
                  ? 'border-[var(--color-accent)] bg-[var(--color-accent-soft)]'
                  : 'border-[var(--color-border-strong)] bg-[var(--color-base-soft)] hover:border-[var(--color-accent-border)]'"
                @click="handleProviderSelect(card.id)"
              >
                <div class="mb-2 inline-flex h-7 w-7 items-center justify-center rounded-md bg-[var(--color-base)] text-[var(--color-text-sub)]">
                  <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8">
                    <path :d="card.icon" />
                  </svg>
                </div>
                <p class="text-sm font-medium text-[var(--color-text-main)]">{{ card.label }}</p>
                <p class="mt-1 text-xs leading-relaxed text-[var(--color-text-muted)]">{{ card.description }}</p>
              </button>
            </div>
          </div>
        </div>
      </div>

      <div class="rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base)]">
        <template v-if="activePanel !== 2 && panel2Ready">
          <div class="flex items-center justify-between px-4 py-3">
            <div class="flex min-w-0 items-center gap-2">
              <p class="truncate text-sm font-medium text-[var(--color-text-main)]">{{ provider === 'ollama' ? 'Ollama connected' : 'API key saved' }}</p>
              <span class="inline-flex items-center gap-1 rounded-full bg-[var(--color-success-bg)] px-2 py-0.5 text-[11px] text-[var(--color-success)]">
                <span class="h-1.5 w-1.5 rounded-full bg-[var(--color-success)]"></span>
                Saved
              </span>
            </div>
            <button
              type="button"
              class="text-xs font-medium text-[var(--color-accent)] hover:brightness-90"
              @click="openPanel(2)"
            >
              Edit
            </button>
          </div>
        </template>

        <div
          class="overflow-hidden transition-all duration-300"
          :class="activePanel === 2 ? 'max-h-[36rem] opacity-100' : 'max-h-0 opacity-0'"
        >
          <div class="space-y-3 px-4 pb-4 pt-2">
            <label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-[var(--color-text-sub)]">
              {{ provider === 'ollama' ? 'Ollama base URL' : 'API key' }}
            </label>

            <div v-if="provider === 'ollama'" class="space-y-3">
              <input
                v-model="ollamaBaseUrl"
                type="text"
                class="w-full rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base-soft)] px-3 py-2 text-sm text-[var(--color-text-main)] outline-none focus:border-[var(--color-accent)] focus:ring-2 focus:ring-[var(--color-accent)]/20"
                placeholder="http://localhost:11434"
              />

              <p
                v-if="refreshNotice"
                class="rounded-lg border border-[var(--color-accent-border)] bg-[var(--color-accent-soft)] px-3 py-2 text-xs text-[var(--color-text-sub)]"
              >
                {{ refreshNotice }}
              </p>

              <div class="flex items-center justify-end">
                <button
                  type="button"
                  class="rounded-lg bg-[var(--color-accent)] px-4 py-2 text-sm font-medium text-white transition-all hover:brightness-90 disabled:cursor-not-allowed disabled:opacity-60"
                  :disabled="refreshLoading"
                  @click="connectOllama"
                >
                  <span v-if="refreshLoading" class="inline-flex items-center gap-2">
                    <span class="h-3 w-3 animate-spin rounded-full border-2 border-white/60 border-t-white"></span>
                    Connecting...
                  </span>
                  <span v-else>Connect</span>
                </button>
              </div>
            </div>

            <div v-else class="space-y-3">
              <div class="relative">
                <input
                  :value="apiKey"
                  :type="showKey ? 'text' : 'password'"
                  class="w-full rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base-soft)] px-3 py-2 pr-10 text-sm text-[var(--color-text-main)] outline-none focus:border-[var(--color-accent)] focus:ring-2 focus:ring-[var(--color-accent)]/20"
                  :placeholder="provider === 'openai' ? 'sk-...' : 'or-...'"
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
                <span
                  v-if="selectedProviderApiKeyPresent"
                  class="inline-flex items-center gap-1 rounded-full bg-[var(--color-success-bg)] px-2 py-0.5 text-[11px] text-[var(--color-success)]"
                >
                  <span class="h-1.5 w-1.5 rounded-full bg-[var(--color-success)]"></span>
                  Saved
                </span>
                <span v-if="verifySuccess" class="text-xs text-[var(--color-success)]">✓ {{ verifySuccess }}</span>
              </div>

              <p v-if="verifyError" class="text-xs text-[var(--color-danger)]">{{ verifyError }}</p>
              <p v-if="verifyWarning" class="text-xs text-[var(--color-info)]">{{ verifyWarning }}</p>
              <p v-if="refreshNotice" class="text-xs text-[var(--color-info)]">{{ refreshNotice }}</p>

              <div class="flex items-center justify-end">
                <button
                  type="button"
                  class="rounded-lg bg-[var(--color-accent)] px-4 py-2 text-sm font-medium text-white transition-all hover:brightness-90 disabled:cursor-not-allowed disabled:opacity-60"
                  :disabled="verifyLoading"
                  @click="verifyAndSave"
                >
                  <span v-if="verifyLoading" class="inline-flex items-center gap-2">
                    <span class="h-3 w-3 animate-spin rounded-full border-2 border-white/60 border-t-white"></span>
                    Verifying...
                  </span>
                  <span v-else>{{ selectedProviderApiKeyPresent ? 'Update key' : 'Verify & save key' }}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base)]">
        <template v-if="activePanel !== 3 && panel3Ready">
          <div class="flex items-center justify-between px-4 py-3">
            <div class="min-w-0">
              <p class="truncate text-sm font-medium text-[var(--color-text-main)]">Models selected</p>
              <p class="truncate text-xs text-[var(--color-text-sub)]">
                Main: {{ selectedMainLabel }} · Lite: {{ selectedLiteLabel }}
              </p>
            </div>
            <button
              type="button"
              class="text-xs font-medium text-[var(--color-accent)] hover:brightness-90"
              @click="openPanel(3)"
            >
              Edit
            </button>
          </div>
        </template>

        <div
          class="overflow-hidden transition-all duration-300"
          :class="activePanel === 3 ? 'max-h-[44rem] opacity-100' : 'max-h-0 opacity-0'"
        >
          <div class="space-y-3 px-4 pb-4 pt-2">
            <div class="grid grid-cols-2 gap-3">
              <div class="space-y-2">
                <label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-[var(--color-text-sub)]">Main model</label>
                <input
                  v-model="mainSearch"
                  type="text"
                  class="w-full rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base-soft)] px-3 py-2 text-sm text-[var(--color-text-main)] outline-none focus:border-[var(--color-accent)] focus:ring-2 focus:ring-[var(--color-accent)]/20"
                  placeholder="Search model"
                />
                <div class="relative">
                  <select
                    v-model="mainModel"
                    class="w-full appearance-none rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base-soft)] px-3 py-2 pr-9 text-sm text-[var(--color-text-main)] outline-none focus:border-[var(--color-accent)] focus:ring-2 focus:ring-[var(--color-accent)]/20"
                  >
                    <option v-for="item in mainOptions" :key="item.id" :value="item.id">{{ item.display_name }}</option>
                  </select>
                  <svg class="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-text-muted)]" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8">
                    <path d="M6 8l4 4 4-4" />
                  </svg>
                </div>
              </div>

              <div class="space-y-2">
                <label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-[var(--color-text-sub)]">
                  Lite model
                  <span class="normal-case tracking-normal font-normal text-xs text-[var(--color-text-muted)]">for quick tasks</span>
                </label>
                <input
                  v-model="liteSearch"
                  type="text"
                  class="w-full rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base-soft)] px-3 py-2 text-sm text-[var(--color-text-main)] outline-none focus:border-[var(--color-accent)] focus:ring-2 focus:ring-[var(--color-accent)]/20"
                  placeholder="Search model"
                />
                <div class="relative">
                  <select
                    v-model="liteModel"
                    class="w-full appearance-none rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base-soft)] px-3 py-2 pr-9 text-sm text-[var(--color-text-main)] outline-none focus:border-[var(--color-accent)] focus:ring-2 focus:ring-[var(--color-accent)]/20"
                  >
                    <option v-for="item in liteOptions" :key="item.id" :value="item.id">{{ item.display_name }}</option>
                  </select>
                  <svg class="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-text-muted)]" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8">
                    <path d="M6 8l4 4 4-4" />
                  </svg>
                </div>
              </div>
            </div>

            <div class="flex items-center justify-between">
              <label v-if="provider !== 'ollama'" class="inline-flex cursor-pointer items-center gap-2 text-xs text-[var(--color-text-sub)]">
                <input v-model="showAllModels" type="checkbox" class="rounded border-[var(--color-border-strong)]" />
                Show all models
              </label>

              <button
                type="button"
                class="inline-flex items-center gap-1 text-xs text-[var(--color-accent)] transition-all hover:brightness-90 disabled:cursor-not-allowed disabled:opacity-60"
                :disabled="refreshLoading"
                @click="refreshModelList"
              >
                <svg viewBox="0 0 24 24" class="h-3.5 w-3.5" :class="refreshLoading ? 'animate-spin' : ''" fill="none" stroke="currentColor" stroke-width="1.8">
                  <path d="M20 12a8 8 0 1 1-2.34-5.66" />
                  <path d="M20 4v6h-6" />
                </svg>
                <span>Refresh model list</span>
              </button>
            </div>

            <p v-if="refreshNotice" class="text-xs text-[var(--color-info)]">{{ refreshNotice }}</p>
          </div>
        </div>
      </div>

      <div class="rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base)]">
        <template v-if="activePanel !== 4 && panel4Ready">
          <div class="flex items-center justify-between px-4 py-3">
            <p class="truncate text-sm font-medium text-[var(--color-text-main)]">Configuration ready</p>
            <button
              type="button"
              class="text-xs font-medium text-[var(--color-accent)] hover:brightness-90"
              @click="openPanel(4)"
            >
              Edit
            </button>
          </div>
        </template>

        <div
          class="overflow-hidden transition-all duration-300"
          :class="activePanel === 4 ? 'max-h-[20rem] opacity-100' : 'max-h-0 opacity-0'"
        >
          <div class="space-y-3 px-4 pb-4 pt-2">
            <p class="rounded-lg border border-[var(--color-accent-border)] bg-[var(--color-accent-soft)] px-3 py-2 text-xs leading-relaxed text-[var(--color-text-sub)]">
              Provider: {{ providerLabel }} · Main: {{ selectedMainLabel }} · Lite: {{ selectedLiteLabel }} · Key: ••••{{ maskedKeySuffix }}
            </p>

            <div class="flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
              <button
                type="button"
                class="rounded-lg border border-[var(--color-border-strong)] px-4 py-2 text-sm text-[var(--color-text-sub)] transition-all hover:bg-[var(--color-base-soft)]"
                @click="emit('close-request')"
              >
                Cancel
              </button>
              <button
                type="button"
                class="rounded-lg bg-[var(--color-accent)] px-4 py-2 text-sm font-medium text-white transition-all hover:brightness-90 disabled:cursor-not-allowed disabled:opacity-60"
                :disabled="saveLoading"
                @click="saveConfiguration"
              >
                <span v-if="saveLoading" class="inline-flex items-center gap-2">
                  <span class="h-3 w-3 animate-spin rounded-full border-2 border-white/60 border-t-white"></span>
                  Saving...
                </span>
                <span v-else>{{ selectedProviderApiKeyPresent ? 'Update configuration' : 'Save configuration' }}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useLLMConfig } from '../../../composables/useLLMConfig'
import { useAppStore } from '../../../stores/appStore'
import { toast } from '../../../composables/useToast'

const emit = defineEmits(['close-request'])

const appStore = useAppStore()
const llm = useLLMConfig()

const {
  provider,
  apiKey,
  ollamaBaseUrl,
  keyVerified,
  mainModels,
  liteModels,
  mainModel,
  liteModel,
  selectedProviderApiKeyPresent,
  verifyLoading,
  verifyError,
  verifyWarning,
  verifySuccess,
  refreshNotice,
  refreshLoading,
  saveLoading,
  providerLabel,
  maskedKeySuffix,
  showAllModels,
  loadPreferences,
  setProvider,
  setApiKey,
  verifyKey,
  saveKey,
  refreshModels,
  saveConfig,
  getModelMeta,
  clearTransientMessages,
} = llm

const showKey = ref(false)
const activePanel = ref(1)
const mainSearch = ref('')
const liteSearch = ref('')

const providerCards = [
  {
    id: 'openai',
    label: 'OpenAI',
    description: 'Direct OpenAI models.',
    icon: 'M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z',
  },
  {
    id: 'openrouter',
    label: 'OpenRouter',
    description: 'Route across providers.',
    icon: 'M4 6h16M4 12h16M4 18h16',
  },
  {
    id: 'ollama',
    label: 'Ollama (local)',
    description: 'Run local models only.',
    icon: 'M4 12h16M12 4v16',
  },
]

const panel2Ready = computed(() => !!provider.value && keyVerified.value)
const panel3Ready = computed(() => panel2Ready.value)
const panel4Ready = computed(() => !!mainModel.value && !!liteModel.value)

const selectedMainLabel = computed(() => getModelLabel(mainModel.value))
const selectedLiteLabel = computed(() => getModelLabel(liteModel.value))

const mainOptions = computed(() => buildModelOptions('main', mainSearch.value, mainModel.value))
const liteOptions = computed(() => buildModelOptions('lite', liteSearch.value, liteModel.value))

onMounted(async () => {
  await loadPreferences(provider.value, false)

  if (!provider.value) {
    activePanel.value = 1
    return
  }
  if (!keyVerified.value) {
    activePanel.value = 2
    return
  }
  if (!panel4Ready.value) {
    activePanel.value = 3
    return
  }
  activePanel.value = 4
})

watch(provider, (next) => {
  if (!next) {
    activePanel.value = 1
    return
  }
  if (activePanel.value < 2) activePanel.value = 2
})

watch([mainModel, liteModel], ([main, lite]) => {
  if (main && lite && keyVerified.value && activePanel.value < 4) {
    activePanel.value = 4
  }
})

function openPanel(panel) {
  activePanel.value = panel
}

function getModelLabel(modelId) {
  if (!modelId) return 'Not selected'
  const model = getModelMeta(provider.value, modelId)
  return model?.display_name || modelId
}

function buildModelOptions(type, query, selectedId) {
  const isMain = type === 'main'
  const ids = isMain ? mainModels.value : liteModels.value
  const normalizedQuery = String(query || '').trim().toLowerCase()

  let options = ids.map((id) => {
    const meta = getModelMeta(provider.value, id)
    return {
      id,
      display_name: meta?.display_name || id,
      tags: Array.isArray(meta?.tags) ? meta.tags : ['recommended'],
    }
  })

  if (provider.value !== 'ollama' && !showAllModels.value) {
    options = options.filter((item) => item.tags.includes('recommended'))
  }

  if (normalizedQuery) {
    options = options.filter((item) => item.display_name.toLowerCase().includes(normalizedQuery))
  }

  if (selectedId && !options.some((item) => item.id === selectedId)) {
    const meta = getModelMeta(provider.value, selectedId)
    options.unshift({
      id: selectedId,
      display_name: meta?.display_name || selectedId,
      tags: Array.isArray(meta?.tags) ? meta.tags : ['recommended'],
    })
  }

  return options
}

function handleProviderSelect(nextProvider) {
  setProvider(nextProvider)
  clearTransientMessages()
  activePanel.value = 2
}

async function verifyAndSave() {
  const verifyResult = await verifyKey()
  if (!verifyResult.ok) {
    return
  }

  const saveResult = await saveKey()
  if (!saveResult.ok) {
    toast.error('Key Save Failed', 'Could not save API key to OS keychain.')
    return
  }

  activePanel.value = 3
  void refreshModels({ background: true })
}

async function connectOllama() {
  const result = await refreshModels()
  if (result.ok) {
    keyVerified.value = true
    activePanel.value = 3
    return
  }

  if (result.error !== 'ollama_unreachable') {
    toast.error('Ollama Error', 'Could not refresh local models.')
  }
}

async function refreshModelList() {
  await refreshModels()
}

async function saveConfiguration() {
  const result = await saveConfig()
  if (!result.ok) {
    toast.error('Save Failed', result.error || 'Failed to save LLM configuration.')
    return
  }

  if (typeof appStore.applyPreferencesResponse === 'function') {
    appStore.applyPreferencesResponse(result.response)
  }
  toast.success('LLM Configuration Saved', 'LLM configuration saved')
  emit('close-request')
}
</script>
