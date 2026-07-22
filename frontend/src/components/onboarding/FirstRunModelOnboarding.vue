<template>
  <div class="onboarding-root fixed inset-0 layer-modal overflow-y-auto bg-[var(--color-base)] text-[var(--color-text-main)]">
    <div class="mx-auto flex min-h-full w-full max-w-6xl flex-col px-6 py-6 sm:px-10 sm:py-8 lg:px-14">
      <header class="onboarding-enter flex items-center gap-3" style="--onboarding-delay: 0ms">
        <img :src="logo" alt="" class="h-9 w-9" />
        <div>
          <p class="text-sm font-semibold tracking-tight">Inquira</p>
          <p class="text-[11px] text-[var(--color-text-muted)]">Local analytics workspace</p>
        </div>
      </header>

      <main class="my-auto grid w-full gap-12 py-12 lg:grid-cols-[minmax(0,0.78fr)_minmax(360px,1fr)] lg:gap-20 lg:py-16">
        <section class="onboarding-enter self-center" style="--onboarding-delay: 70ms" aria-labelledby="onboarding-title">
          <p class="mb-4 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--color-accent-text)]">Step 1 of 3</p>
          <h1 id="onboarding-title" class="max-w-xl text-4xl font-semibold tracking-[-0.035em] sm:text-5xl">
            Connect a model.
          </h1>
          <p class="mt-5 max-w-lg text-sm leading-7 text-[var(--color-text-muted)] sm:text-[15px]">
            Choose the provider Inquira will use for analysis. Your credential stays in the operating system keychain.
          </p>

          <ol class="mt-10 border-y border-[var(--color-border)]">
            <li v-for="step in journeySteps" :key="step.number" class="flex items-start gap-4 border-b border-[var(--color-border)] py-4 last:border-b-0">
              <span
                class="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold"
                :class="step.active ? 'bg-[var(--color-accent)] text-white' : 'bg-[var(--color-base-soft)] text-[var(--color-text-muted)]'"
              >
                {{ step.number }}
              </span>
              <div>
                <p class="text-sm font-medium">{{ step.label }}</p>
                <p class="mt-0.5 text-xs leading-5 text-[var(--color-text-muted)]">{{ step.description }}</p>
              </div>
            </li>
          </ol>
        </section>

        <section class="onboarding-connection-panel onboarding-enter self-center p-6 sm:p-8" style="--onboarding-delay: 140ms" aria-label="Model connection">
          <Transition name="onboarding-success" mode="out-in">
            <div v-if="connected" key="connected" class="py-2" role="status" aria-live="polite">
              <div class="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-success-bg)] text-xl text-[var(--color-success)]">✓</div>
              <h2 class="mt-6 text-2xl font-semibold tracking-tight">{{ providerLabel }} is connected</h2>
              <p class="mt-2 max-w-md text-sm leading-6 text-[var(--color-text-muted)]">
                The connection is ready. Workspace and data setup come next.
              </p>
              <button type="button" class="btn-primary mt-8 min-w-48 px-5 py-2.5" :disabled="completeLoading" @click="finishOnboarding">
                <span v-if="completeLoading" class="inline-flex items-center gap-2">
                  <span class="loading-spinner"></span>
                  Opening Inquira…
                </span>
                <span v-else>Continue to Inquira</span>
              </button>
              <p v-if="actionError" class="mt-4 text-xs leading-5 text-[var(--color-danger-text)]">{{ actionError }}</p>
            </div>

            <div v-else key="form">
              <div class="flex items-start justify-between gap-5">
                <div>
                  <h2 class="text-xl font-semibold tracking-tight">Model provider</h2>
                  <p class="mt-1 text-xs leading-5 text-[var(--color-text-muted)]">This connection is shared across local workspaces.</p>
                </div>
                <span class="mt-1 whitespace-nowrap text-[11px] font-medium text-[var(--color-text-muted)]">Not connected</span>
              </div>

              <div class="mt-7">
                <label class="input-label">Provider</label>
                <HeaderDropdown
                  :model-value="provider"
                  :options="providerOptions"
                  max-width-class="w-full"
                  aria-label="Model provider"
                  @update:model-value="handleProviderSelect"
                />
              </div>

              <Transition name="onboarding-shift" mode="out-in">
                <div :key="provider" class="mt-6">
                  <div v-if="provider === 'ollama'">
                    <label for="onboarding-ollama-url" class="input-label">Ollama base URL</label>
                    <input
                      id="onboarding-ollama-url"
                      v-model="ollamaBaseUrl"
                      class="text-input"
                      type="url"
                      autocomplete="url"
                      placeholder="http://localhost:11434"
                      @input="clearMessages"
                    />
                    <p class="mt-2 text-xs leading-5 text-[var(--color-text-muted)]">Ollama must be running before the connection can be tested.</p>
                  </div>

                  <div v-else>
                    <label for="onboarding-api-key" class="input-label">{{ apiKeyLabel }}</label>
                    <div class="relative">
                      <input
                        id="onboarding-api-key"
                        :value="apiKey"
                        :type="showKey ? 'text' : 'password'"
                        class="text-input pr-12 font-mono"
                        autocomplete="off"
                        spellcheck="false"
                        :placeholder="apiKeyPlaceholder"
                        @input="setApiKey($event.target.value)"
                      />
                      <button type="button" class="eye-toggle-btn" :aria-label="showKey ? 'Hide key' : 'Show key'" @click="showKey = !showKey">
                        <span aria-hidden="true">{{ showKey ? 'Hide' : 'Show' }}</span>
                      </button>
                    </div>
                    <button type="button" class="mt-2 text-xs font-medium text-[var(--color-accent-text)] hover:underline" @click="openKeyPortal">
                      Create a {{ providerLabel }} API key
                    </button>
                  </div>
                </div>
              </Transition>

              <p v-if="connectionError" class="mt-5 text-xs leading-5 text-[var(--color-danger-text)]" role="alert">{{ connectionError }}</p>

              <button
                type="button"
                class="btn-primary mt-7 w-full px-5 py-2.5"
                :disabled="connectLoading || !canConnect"
                @click="connectProvider"
              >
                <span v-if="connectLoading" class="inline-flex items-center gap-2">
                  <span class="loading-spinner"></span>
                  {{ provider === 'ollama' ? 'Testing Ollama…' : 'Verifying key…' }}
                </span>
                <span v-else>{{ connectButtonLabel }}</span>
              </button>

              <div class="mt-7 flex gap-3 border-t border-[var(--color-border)] pt-5 text-xs leading-5 text-[var(--color-text-muted)]">
                <svg class="mt-0.5 h-4 w-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
                  <rect x="5" y="10" width="14" height="10" rx="2" />
                  <path d="M8 10V7a4 4 0 0 1 8 0v3" />
                </svg>
                <p>API keys are never stored in the Inquira database. Provider requests use your system proxy and certificate settings.</p>
              </div>
            </div>
          </Transition>
        </section>
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import HeaderDropdown from '../ui/HeaderDropdown.vue'
import { useLLMConfig } from '../../composables/useLLMConfig'
import { modelConnectionService } from '../../services/modelConnectionService'
import { openExternalUrl } from '../../services/externalLinkService'
import { extractApiErrorMessage } from '../../utils/apiError'
import logo from '../../assets/favicon.svg'

const props = defineProps({
  initialStatus: {
    type: Object,
    default: () => ({}),
  },
})

const emit = defineEmits(['complete'])
const llm = useLLMConfig()
const {
  provider,
  apiKey,
  ollamaBaseUrl,
  selectedProviderApiKeyPresent,
  usingMaskedKey,
  verifyError,
  loadPreferences,
  setProvider,
  setApiKey,
  verifyAndSaveKey,
  clearTransientMessages,
} = llm

const showKey = ref(false)
const connectLoading = ref(false)
const completeLoading = ref(false)
const connected = ref(Boolean(props.initialStatus?.connection_ready))
const actionError = ref(String(props.initialStatus?.error || ''))

const providerOptions = [
  { value: 'openrouter', label: 'OpenRouter' },
  { value: 'openai', label: 'OpenAI' },
  { value: 'ollama', label: 'Ollama (local)' },
]

const journeySteps = [
  { number: 1, label: 'Connect a model', description: 'Verify one shared provider connection.', active: true },
  { number: 2, label: 'Create a workspace', description: 'Keep related data and analysis together.', active: false },
  { number: 3, label: 'Add local data', description: 'Connect a file when the workspace is ready.', active: false },
]

const providerLabel = computed(() => {
  if (provider.value === 'openai') return 'OpenAI'
  if (provider.value === 'ollama') return 'Ollama'
  return 'OpenRouter'
})
const apiKeyLabel = computed(() => `${providerLabel.value} API key`)
const apiKeyPlaceholder = computed(() => (provider.value === 'openai' ? 'sk-…' : 'or-…'))
const connectionError = computed(() => String(actionError.value || verifyError.value || '').trim())
const canConnect = computed(() => {
  if (provider.value === 'ollama') return Boolean(String(ollamaBaseUrl.value || '').trim())
  return Boolean(String(apiKey.value || '').trim())
})
const connectButtonLabel = computed(() => {
  if (provider.value === 'ollama') return 'Test and connect Ollama'
  if (selectedProviderApiKeyPresent.value && usingMaskedKey.value) return `Use saved ${providerLabel.value} key`
  return 'Verify and save key'
})
const keyPortal = computed(() => (
  provider.value === 'openai' ? 'https://platform.openai.com/api-keys' : 'https://openrouter.ai/keys'
))

onMounted(async () => {
  try {
    await loadPreferences(props.initialStatus?.provider || null, false)
  } catch (error) {
    actionError.value = extractApiErrorMessage(error, 'Could not load model providers.')
  }
})

function clearMessages() {
  actionError.value = ''
  clearTransientMessages()
}

async function handleProviderSelect(nextProvider) {
  const normalized = String(nextProvider || '').trim().toLowerCase()
  if (!normalized || normalized === provider.value) return
  connected.value = false
  showKey.value = false
  clearMessages()
  setProvider(normalized)
  try {
    await loadPreferences(normalized, false)
  } catch (error) {
    actionError.value = extractApiErrorMessage(error, 'Could not load this provider.')
  }
}

async function connectProvider() {
  connectLoading.value = true
  clearMessages()
  try {
    const selectedProvider = String(provider.value || 'openrouter')
    if (selectedProvider === 'ollama') {
      const response = await modelConnectionService.setApiKey({
        provider: 'ollama',
        base_url: String(ollamaBaseUrl.value || '').trim(),
      })
      if (response?.warning) {
        actionError.value = 'Could not reach Ollama. Check the URL and confirm Ollama is running.'
      }
    } else if (usingMaskedKey.value && selectedProviderApiKeyPresent.value) {
      await modelConnectionService.setApiKey({ provider: selectedProvider })
    } else {
      const result = await verifyAndSaveKey()
      if (!result.ok) {
        if (result.error === 'network_error') {
          actionError.value = 'Could not reach the provider. Check your network, proxy, and company certificates.'
        }
        return
      }
    }

    const status = await modelConnectionService.getOnboardingStatus()
    if (!status?.connection_ready) {
      actionError.value = selectedProvider === 'ollama'
        ? 'Could not reach Ollama. Check the URL and confirm Ollama is running.'
        : 'The provider connection was not saved. Please try again.'
      return
    }
    connected.value = true
  } catch (error) {
    actionError.value = extractApiErrorMessage(error, 'Could not connect this provider.')
  } finally {
    connectLoading.value = false
  }
}

async function finishOnboarding() {
  completeLoading.value = true
  actionError.value = ''
  try {
    const status = await modelConnectionService.completeOnboarding()
    emit('complete', status)
  } catch (error) {
    actionError.value = extractApiErrorMessage(error, 'Could not finish setup.')
  } finally {
    completeLoading.value = false
  }
}

function openKeyPortal() {
  void openExternalUrl(keyPortal.value)
}
</script>

<style scoped>
.onboarding-root {
  background: var(--color-base);
}

.onboarding-connection-panel {
  background: var(--color-surface-raised);
  border: 1px solid color-mix(in srgb, var(--color-border) 84%, var(--color-text-main) 16%);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-overlay), inset 0 1px 0 color-mix(in srgb, var(--color-text-main) 4%, transparent);
}

.onboarding-enter {
  animation: onboarding-enter var(--motion-duration-entrance) var(--motion-ease-spring) both;
  animation-delay: var(--onboarding-delay, 0ms);
}

.onboarding-shift-enter-active,
.onboarding-shift-leave-active,
.onboarding-success-enter-active,
.onboarding-success-leave-active {
  transition:
    opacity var(--motion-duration-standard) var(--motion-ease-standard),
    transform var(--motion-duration-standard) var(--motion-ease-standard);
}

.onboarding-shift-enter-from,
.onboarding-success-enter-from {
  opacity: 0;
  transform: translateY(6px);
}

.onboarding-shift-leave-to,
.onboarding-success-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

@keyframes onboarding-enter {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .onboarding-enter {
    animation: none;
  }

  .onboarding-shift-enter-active,
  .onboarding-shift-leave-active,
  .onboarding-success-enter-active,
  .onboarding-success-leave-active {
    transition: none;
  }
}
</style>
