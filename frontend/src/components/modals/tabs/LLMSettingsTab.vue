<template>
  <section class="scrollbar-hidden relative h-full overflow-y-auto">
    <div class="scrollbar-hidden h-full overflow-y-auto pb-8">


      <div class="llm-settings-container">
        <!-- 1. Provider connection -->
        <div class="flex items-end justify-between gap-5 border-b border-[var(--color-border)] pb-5">
          <div class="min-w-0 flex-1">
            <label class="input-label">Connection provider</label>
            <HeaderDropdown
              :model-value="provider"
              :options="providerOptions"
              max-width-class="w-full"
              aria-label="Credential provider"
              @update:model-value="handleProviderSelect"
            />
            <p class="mt-1.5 text-xs text-[var(--color-text-muted)]">Choose a provider to manage its shared application credential.</p>
          </div>
          <div class="status-badge mb-0.5 shrink-0" :class="statusBadgeClass">
            <span class="status-dot"></span>
            <span>{{ statusBadgeText }}</span>
          </div>
        </div>

        <!-- 2. Credentials & Connection settings card -->
        <div class="settings-card glass-panel">
          <div class="settings-card-header">
            <h3 class="settings-card-title">
              {{ provider === 'ollama' ? 'Connection Settings' : 'API Credentials' }}
            </h3>
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
              <div v-if="provider === 'openai-compatible'" class="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <label class="input-group sm:col-span-2">
                  <span class="input-label">Base URL</span>
                  <input v-model="compatibleBaseUrl" type="url" class="text-input font-mono" placeholder="https://models.company.example/v1" autocomplete="url" spellcheck="false" />
                  <span class="input-hint">Use the API root before <span class="font-mono">/chat/completions</span>. Azure-style API versions are supported below.</span>
                </label>
                <label class="input-group">
                  <span class="input-label">API key header</span>
                  <input v-model="apiKeyHeader" type="text" class="text-input font-mono" placeholder="Authorization or api-key" autocomplete="off" spellcheck="false" />
                </label>
                <label class="input-group">
                  <span class="input-label">Header prefix</span>
                  <input v-model="apiKeyPrefix" type="text" class="text-input font-mono" placeholder="Bearer (leave empty for api-key)" autocomplete="off" spellcheck="false" />
                </label>
                <label class="input-group">
                  <span class="input-label">API version</span>
                  <input v-model="apiVersion" type="text" class="text-input font-mono" placeholder="2024-10-21 (optional)" autocomplete="off" spellcheck="false" />
                </label>
                <label class="input-group">
                  <span class="input-label">Organization</span>
                  <input v-model="organization" type="text" class="text-input font-mono" placeholder="Optional organization ID" autocomplete="off" spellcheck="false" />
                </label>
                <label class="input-group sm:col-span-2">
                  <span class="input-label">Project</span>
                  <input v-model="project" type="text" class="text-input font-mono" placeholder="Optional project ID" autocomplete="off" spellcheck="false" />
                </label>
              </div>

              <div class="input-group">
                <label class="input-label">{{ apiKeyLabel }}</label>
                <div class="relative">
                  <input
                    :value="apiKey"
                    :type="showKey ? 'text' : 'password'"
                    class="text-input pr-12 font-mono"
                    :placeholder="apiKeyPlaceholder"
                    @input="handleApiKeyInput"
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
                  ref="credentialMenuButton"
                  type="button"
                  class="btn-icon h-9 w-9 border border-[var(--color-border)]"
                  :disabled="verifyLoading || saveLoading || deleteLoading"
                  title="Credential actions"
                  aria-label="Credential actions"
                  @click="openCredentialMenu"
                >
                  <span aria-hidden="true">•••</span>
                </button>

                <Transition name="motion-fade">
                  <span v-if="verifySuccessMessage" class="success-message">
                    <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                    {{ verifySuccessMessage }}
                  </span>
                </Transition>
              </div>

              <Transition name="motion-fade">
                <p v-if="verifyError" class="error-message-text">{{ verifyError }}</p>
              </Transition>

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

            <div class="mt-5 border-t border-[var(--color-border)] pt-4">
              <div class="mb-3">
                <h4 class="text-sm font-semibold text-[var(--color-text-main)]">Provider network override</h4>
                <p class="mt-1 text-xs leading-5 text-[var(--color-text-muted)]">Inherit the global proxy by default, or choose a connection policy for this provider.</p>
              </div>
              <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <label class="input-group sm:col-span-2">
                  <span class="input-label">Proxy policy</span>
                  <HeaderDropdown
                    :model-value="providerNetworkMode"
                    :options="providerNetworkOptions"
                    max-width-class="w-full"
                    aria-label="Provider proxy policy"
                    @update:model-value="providerNetworkMode = String($event || 'inherit')"
                  />
                </label>
                <label v-if="providerNetworkMode === 'custom'" class="input-group sm:col-span-2">
                  <span class="input-label">Proxy URL</span>
                  <input v-model="providerProxyUrl" type="url" class="text-input font-mono" placeholder="http://proxy.company:8080" autocomplete="off" spellcheck="false" />
                </label>
                <label v-if="providerNetworkMode === 'custom'" class="input-group sm:col-span-2">
                  <span class="input-label">Bypass proxy for</span>
                  <input v-model="providerNoProxy" type="text" class="text-input font-mono" placeholder="localhost,.company.internal,10.0.0.0/8" autocomplete="off" spellcheck="false" />
                </label>
                <label class="input-group sm:col-span-2">
                  <span class="input-label">CA certificate bundle</span>
                  <span class="flex gap-2">
                    <input v-model="providerCaBundlePath" type="text" class="text-input min-w-0 flex-1 font-mono" placeholder="Optional PEM certificate bundle" autocomplete="off" spellcheck="false" />
                    <button type="button" class="btn-secondary px-3 py-1.5 text-xs" @click="chooseProviderCertificate('ca')">Browse</button>
                  </span>
                </label>
                <template v-if="provider === 'openai-compatible'">
                  <label class="input-group sm:col-span-2">
                    <span class="input-label">Client certificate</span>
                    <span class="flex gap-2">
                      <input v-model="providerClientCertificatePath" type="text" class="text-input min-w-0 flex-1 font-mono" placeholder="Optional PEM client certificate" autocomplete="off" spellcheck="false" />
                      <button type="button" class="btn-secondary px-3 py-1.5 text-xs" @click="chooseProviderCertificate('client')">Browse</button>
                    </span>
                  </label>
                  <label class="input-group sm:col-span-2">
                    <span class="input-label">Client private key</span>
                    <span class="flex gap-2">
                      <input v-model="providerClientKeyPath" type="text" class="text-input min-w-0 flex-1 font-mono" placeholder="Optional PEM private key" autocomplete="off" spellcheck="false" />
                      <button type="button" class="btn-secondary px-3 py-1.5 text-xs" @click="chooseProviderPrivateKey">Browse</button>
                    </span>
                  </label>
                </template>
              </div>
            </div>

            <p v-if="refreshNotice" class="info-message-text">{{ refreshNotice }}</p>
          </div>
        </div>

        <section class="mt-6 border-t border-[var(--color-border)] pt-4">
          <button
            type="button"
            class="w-full cursor-pointer rounded-md py-2 text-left text-sm font-semibold text-[var(--color-text-main)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent-border)]"
            :aria-expanded="applicationDefaultsOpen"
            @click="applicationDefaultsOpen = !applicationDefaultsOpen"
          >
            <span class="flex items-center justify-between gap-4">
              <span>
                <span class="block">Application model defaults</span>
                <span class="mt-1 block text-xs font-normal text-[var(--color-text-muted)]">Fallback values for workspaces that choose to inherit defaults.</span>
              </span>
              <span class="inline-flex items-center gap-2 text-xs font-normal text-[var(--color-text-muted)]">
                Optional
                <span class="inline-block transition-transform" :class="applicationDefaultsOpen ? 'rotate-90' : ''" aria-hidden="true">›</span>
              </span>
            </span>
          </button>

          <div class="motion-disclosure" :class="applicationDefaultsOpen ? 'motion-disclosure-open' : ''" :aria-hidden="!applicationDefaultsOpen">
          <div class="motion-disclosure-content">

        <!-- 3. Model Configuration Dashboard -->
        <div class="settings-card glass-panel mt-3">
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
				<input
					v-if="provider === 'openai-compatible'"
					v-model="mainModel"
					type="text"
					class="text-input font-mono"
					placeholder="Provider model ID"
					autocomplete="off"
					spellcheck="false"
				/>
                <HeaderDropdown
					v-else
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
				<input
					v-if="provider === 'openai-compatible'"
					v-model="liteModel"
					type="text"
					class="text-input font-mono"
					placeholder="Provider lite model ID"
					autocomplete="off"
					spellcheck="false"
				/>
                <HeaderDropdown
					v-else
                  :model-value="liteModel"
                  :options="liteOptions"
                  :searchable="true"
                  :max-options-without-search="100"
                  search-placeholder="Search model"
                  placeholder="Select lite model"
                  max-width-class="w-full"
                  aria-label="Lite model"
                  @update:model-value="handleLiteModelSelect"
                />
                <p class="model-select-desc">Used for quick tasks, short summaries, and title generation.</p>
              </div>
            </div>

            <!-- Toggle options footer inside model card -->
            <div class="model-controls-footer">
				<label v-if="provider !== 'ollama' && provider !== 'openai-compatible'" class="toggle-switch-label">
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

        <!-- 4. Advanced application defaults -->
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

          <div class="advanced-content-container motion-disclosure" :class="showAdvanced ? 'motion-disclosure-open' : ''" :aria-hidden="!showAdvanced">
            <div class="motion-disclosure-content">
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

          <div class="mt-5 flex items-center justify-end border-t border-[var(--color-border)] pt-4">
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
              <span v-else>Save application defaults</span>
            </button>
          </div>
          </div>
          </div>
        </section>
      </div>
    </div>
  </section>
  <FloatingActionMenu
    :is-open="credentialMenuOpen"
    :position="credentialMenuPosition"
    :items="credentialMenuItems"
    marker-attr="data-credential-actions-menu"
    :height="56"
    @select="handleCredentialMenuSelect"
    @close="credentialMenuOpen = false"
  />
  <ConfirmationModal
    :is-open="deleteCredentialDialogOpen"
    title="Delete saved credential"
    :message="`Remove the saved ${providerDisplayName} credential? Workspaces using this provider will stop working until another key is saved.`"
    confirm-text="Delete credential"
    cancel-text="Cancel"
    @close="deleteCredentialDialogOpen = false"
    @confirm="confirmDeleteCredential"
  />
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import HeaderDropdown from '../../ui/HeaderDropdown.vue'
import FloatingActionMenu from '../../ui/FloatingActionMenu.vue'
import ConfirmationModal from '../ConfirmationModal.vue'
import { modelConnectionService } from '../../../services/modelConnectionService'
import { runtimeProvisionService } from '../../../services/runtimeProvisionService'
import { useLLMConfig } from '../../../composables/useLLMConfig'
import { useUiStore } from '../../../stores/uiStore'
import { usePreferencesStore } from '../../../stores/preferencesStore'
import { useArtifactStore } from '../../../stores/artifactStore'
import { useExecutionStore } from '../../../stores/executionStore'
import { useWorkspaceStore } from '../../../stores/workspaceStore'
import { useConversationStore } from '../../../stores/conversationStore'
import { useWorkspaceActivation } from '../../../composables/useWorkspaceActivation'
import { useArtifactPresentation } from '../../../composables/useArtifactPresentation'
import { useAuthStore } from '../../../stores/authStore'
import { toast } from '../../../composables/useToast'
import { openExternalUrl } from '../../../services/externalLinkService'

const emit = defineEmits(['close-request'])

const uiStore = useUiStore()
const preferencesStore = usePreferencesStore()
const artifactStore = useArtifactStore()
const executionStore = useExecutionStore()
const workspaceStore = useWorkspaceStore()
const conversationStore = useConversationStore()
const workspaceActivation = useWorkspaceActivation()
const artifactPresentation = useArtifactPresentation()
const authStore = useAuthStore()
const llm = useLLMConfig()

const {
  provider,
  apiKey,
  ollamaBaseUrl,
	compatibleBaseUrl,
	apiKeyHeader,
	apiKeyPrefix,
	apiVersion,
	organization,
	project,
	providerNetworkMode,
	providerProxyUrl,
	providerNoProxy,
	providerCaBundlePath,
	providerClientCertificatePath,
	providerClientKeyPath,
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
const applicationDefaultsOpen = ref(false)
const showAdvanced = ref(false)
const deleteLoading = ref(false)
const credentialMenuButton = ref<HTMLElement | null>(null)
const credentialMenuOpen = ref(false)
const credentialMenuPosition = ref({ x: 0, y: 0 })
const deleteCredentialDialogOpen = ref(false)
const credentialMenuItems = computed(() => [{ id: 'delete', label: 'Delete saved credential', destructive: true }])

const providerOptions = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'openrouter', label: 'OpenRouter' },
	{ value: 'anthropic', label: 'Anthropic' },
	{ value: 'openai-compatible', label: 'OpenAI compatible' },
  { value: 'ollama', label: 'Ollama (local)' },
]
const providerNetworkOptions = [
	{ value: 'inherit', label: 'Use global proxy settings' },
	{ value: 'system', label: 'Use system proxy' },
	{ value: 'custom', label: 'Use custom proxy' },
	{ value: 'direct', label: 'Connect directly' },
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
const apiKeyLabel = computed(() => `${providerDisplayName.value} API key`)
const apiKeyPlaceholder = computed(() => {
	if (provider.value === 'openrouter') return 'or-...'
	if (provider.value === 'anthropic') return 'sk-ant-...'
	return 'Enter API key'
})
const providerDisplayName = computed(() => {
	if (provider.value === 'openai') return 'OpenAI'
	if (provider.value === 'openrouter') return 'OpenRouter'
	if (provider.value === 'anthropic') return 'Anthropic'
	if (provider.value === 'openai-compatible') return 'OpenAI compatible provider'
	return 'Ollama'
})
const providerApiKeyPortal = computed(() => {
  if (provider.value === 'openai') return 'https://platform.openai.com/api-keys'
  if (provider.value === 'openrouter') return 'https://openrouter.ai/keys'
	if (provider.value === 'anthropic') return 'https://console.anthropic.com/settings/keys'
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
		frequencyPenalty: selectedProvider === 'openai' || selectedProvider === 'openai-compatible',
		presencePenalty: selectedProvider === 'openai' || selectedProvider === 'openai-compatible',
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

function handleApiKeyInput(event: Event) {
  setApiKey((event.target as HTMLInputElement).value)
}

async function chooseProviderCertificate(kind: 'ca' | 'client') {
	try {
		const selected = await runtimeProvisionService.chooseCertificateBundle()
		if (!selected) return
		if (kind === 'client') providerClientCertificatePath.value = String(selected)
		else providerCaBundlePath.value = String(selected)
	} catch (_error) {
		toast.error('File picker failed', 'Could not choose a certificate file.')
	}
}

async function chooseProviderPrivateKey() {
	try {
		const selected = await runtimeProvisionService.choosePrivateKey()
		if (selected) providerClientKeyPath.value = String(selected)
	} catch (_error) {
		toast.error('File picker failed', 'Could not choose a private key file.')
	}
}

function handleLiteModelSelect(value: string | number | null) {
  liteModel.value = value === null ? null : String(value)
}

function buildModelOptions(type: 'main' | 'lite', selectedId: string | null) {
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

async function searchProviderModels(query: string, limit = 25) {
  const normalizedProvider = String(provider.value || '').trim()
  if (!normalizedProvider) return []
  const response = await modelConnectionService.searchModels(normalizedProvider, query, limit)
  if (Array.isArray(response)) return response
  return Array.isArray(response.models) ? response.models : []
}

async function handleProviderSelect(nextProvider: unknown) {
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

function openCredentialMenu() {
  const rect = credentialMenuButton.value?.getBoundingClientRect?.()
  credentialMenuPosition.value = { x: Number(rect?.right || 0) - 176, y: Number(rect?.bottom || 0) + 6 }
  credentialMenuOpen.value = true
}

function handleCredentialMenuSelect(action: string) {
  if (action === 'delete') deleteCredentialDialogOpen.value = true
}

async function confirmDeleteCredential() {
  deleteCredentialDialogOpen.value = false
  await handleDeleteSavedKey()
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

  if (typeof preferencesStore.applyPreferencesResponse === 'function') {
    preferencesStore.applyPreferencesResponse(result.response)
  }
  toast.success('Configuration saved', 'Configuration saved')
}
</script>
