<template>
  <section class="space-y-4">
    <h2 class="text-lg font-bold text-[var(--color-text-main)]">LLM &amp; API Keys</h2>

    <div class="max-h-[34rem] space-y-5 overflow-y-auto pr-1">
      <div class="space-y-3">
        <label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-[var(--color-text-sub)]">Choose provider</label>
        <div class="grid grid-cols-3 gap-2">
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

      <div class="border-t border-[var(--color-border)]"></div>

      <div class="space-y-3">
        <label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-[var(--color-text-sub)]">
          {{ provider === 'ollama' ? 'Ollama base URL' : apiKeyLabel }}
        </label>

        <div v-if="provider === 'ollama'" class="space-y-2">
          <input
            v-model="ollamaBaseUrl"
            type="text"
            class="w-full rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base-soft)] px-3 py-2 text-sm text-[var(--color-text-main)] outline-none focus:border-[var(--color-accent)] focus:ring-2 focus:ring-[var(--color-accent)]/20"
            placeholder="http://localhost:11434"
          />
        </div>

        <div v-else class="space-y-2">
          <div class="relative">
            <input
              :value="apiKey"
              :type="showKey ? 'text' : 'password'"
              class="w-full rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base-soft)] px-3 py-2 pr-10 text-sm text-[var(--color-text-main)] outline-none focus:border-[var(--color-accent)] focus:ring-2 focus:ring-[var(--color-accent)]/20"
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

          <p v-if="showVerifyOnSaveNote" class="text-xs text-[var(--color-text-muted)]">Key will be verified on save</p>
          <p v-if="verifyError" class="text-xs text-[var(--color-danger)]">{{ verifyError }}</p>
          <p v-if="refreshNotice" class="text-xs text-[var(--color-info)]">{{ refreshNotice }}</p>
        </div>
      </div>

      <div class="border-t border-[var(--color-border)]"></div>

      <div class="space-y-3">
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

        <p v-if="provider !== 'ollama' && verifyWarning" class="text-xs text-[var(--color-info)]">{{ verifyWarning }}</p>
      </div>
    </div>

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
        class="rounded-lg bg-[var(--color-accent)] px-4 py-2 text-sm font-medium text-white transition-all hover:brightness-90"
        @click="saveConfiguration"
      >
        <span v-if="verifyLoading" class="inline-flex items-center gap-2">
          <span class="h-3 w-3 animate-spin rounded-full border-2 border-white/60 border-t-white"></span>
          Verifying...
        </span>
        <span v-else-if="saveLoading" class="inline-flex items-center gap-2">
          <span class="h-3 w-3 animate-spin rounded-full border-2 border-white/60 border-t-white"></span>
          Saving...
        </span>
        <span v-else>Save configuration</span>
      </button>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
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
  mainModels,
  liteModels,
  mainModel,
  liteModel,
  keyMask,
  usingMaskedKey,
  verifyLoading,
  verifyError,
  verifyWarning,
  refreshNotice,
  refreshLoading,
  saveLoading,
  showAllModels,
  loadPreferences,
  setProvider,
  setApiKey,
  refreshModels,
  saveConfig,
  getModelMeta,
  clearTransientMessages,
} = llm

const showKey = ref(false)
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

const apiKeyLabel = computed(() => (provider.value === 'openai' ? 'OpenAI API key' : 'OpenRouter API key'))
const apiKeyPlaceholder = computed(() => (provider.value === 'openai' ? 'sk-...' : 'or-...'))
const showVerifyOnSaveNote = computed(() => (
  provider.value !== 'ollama' &&
  !usingMaskedKey.value &&
  !!String(apiKey.value || '').trim()
))

const mainOptions = computed(() => buildModelOptions('main', mainSearch.value, mainModel.value))
const liteOptions = computed(() => buildModelOptions('lite', liteSearch.value, liteModel.value))

onMounted(async () => {
  await loadPreferences(provider.value, false)
})

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

async function handleProviderSelect(nextProvider) {
  if (provider.value === nextProvider) return
  setProvider(nextProvider)
  clearTransientMessages()
  try {
    await loadPreferences(nextProvider, false)
  } catch (_error) {
    toast.error('Provider Error', 'Could not load provider configuration.')
  }
}

async function refreshModelList() {
  await refreshModels()
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
  emit('close-request')
}
</script>
