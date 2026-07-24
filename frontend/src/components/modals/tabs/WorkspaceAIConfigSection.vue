<template>
  <section>
    <div>
      <h4 class="section-label">Models &amp; privacy</h4>
      <p class="mt-1 text-xs text-[var(--color-text-muted)]">{{ effectiveSummary }}</p>
    </div>

    <div class="mt-3 flex items-center gap-2 text-[11px] text-[var(--color-text-muted)]">
      <span class="h-1.5 w-1.5 rounded-full" :class="config?.readiness?.credential_ready ? 'bg-[var(--color-success)]' : 'bg-[var(--color-warning)]'"></span>
      <span>{{ credentialLabel }}</span>
      <span aria-hidden="true">·</span>
      <span>{{ hasOverrides ? 'Workspace override' : 'Application defaults' }}</span>
      <button v-if="config && !config.readiness?.credential_ready" type="button" class="font-semibold text-[var(--color-accent)] hover:underline" @click="uiStore.openSettings('connections')">Manage connection</button>
    </div>

    <div class="mt-3 space-y-4 border-t border-[var(--color-border)] pt-3">
      <label class="flex items-center justify-between gap-4">
        <span><span class="block text-sm font-medium text-[var(--color-text-main)]">Use application defaults</span><span class="mt-0.5 block text-xs text-[var(--color-text-muted)]">Inherit the secondary defaults stored under Connections.</span></span>
        <input v-model="useDefaults" type="checkbox" class="h-4 w-4 accent-[var(--color-accent)]" />
      </label>

      <div v-if="!useDefaults" class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div class="md:col-span-2">
          <label class="input-label">Provider</label>
          <HeaderDropdown v-model="form.provider" :options="providerOptions" aria-label="Workspace provider" max-width-class="w-full" @update:model-value="loadProviderModels" />
        </div>
        <div>
          <label class="input-label">Main model</label>
          <HeaderDropdown v-model="form.mainModel" :options="mainModelOptions" :searchable="true" aria-label="Workspace main model" max-width-class="w-full" />
          <p class="mt-1 text-[11px] text-[var(--color-text-muted)]">Analysis and reasoning</p>
        </div>
        <div>
          <label class="input-label">Lite model</label>
          <HeaderDropdown v-model="form.liteModel" :options="liteModelOptions" :searchable="true" aria-label="Workspace lite model" max-width-class="w-full" />
          <p class="mt-1 text-[11px] text-[var(--color-text-muted)]">Quick supporting tasks</p>
        </div>
        <div class="md:col-span-2">
          <label class="input-label">Coding model</label>
          <HeaderDropdown v-model="form.codingModel" :options="codingModelOptions" :searchable="true" aria-label="Workspace coding model" max-width-class="w-full" />
          <p class="mt-1 text-[11px] text-[var(--color-text-muted)]">Code generation and repair</p>
        </div>
      </div>

      <label class="flex items-start gap-3 border-t border-[var(--color-border)] pt-3">
        <input v-model="form.allowDataSamples" type="checkbox" class="mt-0.5 h-4 w-4 accent-[var(--color-accent)]" />
        <span><span class="block text-sm font-medium text-[var(--color-text-main)]">Allow bounded data samples in model prompts</span><span class="mt-1 block text-xs leading-relaxed text-[var(--color-text-muted)]">Off keeps row previews local. This permission applies only to this workspace.</span></span>
      </label>

      <section v-if="!useDefaults" class="border-t border-[var(--color-border)] pt-3">
        <button type="button" class="flex w-full items-center justify-between text-left text-xs font-semibold text-[var(--color-text-sub)]" :aria-expanded="advancedOpen" @click="advancedOpen = !advancedOpen">
          <span>Advanced generation controls</span>
          <span class="inline-block transition-transform" :class="advancedOpen ? 'rotate-90' : ''" aria-hidden="true">›</span>
        </button>
        <div class="motion-disclosure" :class="advancedOpen ? 'motion-disclosure-open' : ''" :aria-hidden="!advancedOpen">
        <div class="motion-disclosure-content">
        <div class="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
          <label><span class="input-label">Temperature</span><input v-model.number="form.temperature" type="number" min="0" max="2" step="0.1" class="input-base input-outlined" placeholder="Default" /></label>
          <label><span class="input-label">Max tokens</span><input v-model.number="form.maxTokens" type="number" min="1" max="131072" class="input-base input-outlined" placeholder="Default" /></label>
          <label><span class="input-label">Top P</span><input v-model.number="form.topP" type="number" min="0" max="1" step="0.05" class="input-base input-outlined" placeholder="Default" /></label>
        </div>
        </div>
        </div>
      </section>

      <div class="flex items-center justify-between gap-3 border-t border-[var(--color-border)] pt-3">
        <p class="text-xs" :class="errorMessage ? 'text-[var(--color-danger)]' : isDirty ? 'text-[var(--color-accent)]' : 'text-[var(--color-text-muted)]'">{{ errorMessage || (isDirty ? 'Unsaved changes' : saveStateLabel) }}</p>
        <button type="button" class="btn-primary px-3 py-1.5 text-xs disabled:cursor-not-allowed disabled:opacity-50" :disabled="isSaving || !isDirty" @click="save">{{ isSaving ? 'Saving…' : 'Save AI settings' }}</button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { preferencesApi } from '../../../api/preferences'
import { useUiStore } from '../../../stores/uiStore'
import { usePreferencesStore } from '../../../stores/preferencesStore'
import { useArtifactStore } from '../../../stores/artifactStore'
import { useExecutionStore } from '../../../stores/executionStore'
import { useWorkspaceStore } from '../../../stores/workspaceStore'
import { useConversationStore } from '../../../stores/conversationStore'
import { useWorkspaceActivation } from '../../../composables/useWorkspaceActivation'
import { useArtifactPresentation } from '../../../composables/useArtifactPresentation'
import HeaderDropdown from '../../ui/HeaderDropdown.vue'

const props = defineProps({ workspaceId: { type: String, required: true } })
const uiStore = useUiStore()
const preferencesStore = usePreferencesStore()
const artifactStore = useArtifactStore()
const executionStore = useExecutionStore()
const workspaceStore = useWorkspaceStore()
const conversationStore = useConversationStore()
const workspaceActivation = useWorkspaceActivation()
const artifactPresentation = useArtifactPresentation()
const advancedOpen = ref(false)
const isSaving = ref(false)
const errorMessage = ref('')
const saveStateLabel = ref('Changes apply to this workspace only.')
const providerCatalog = ref(null)
const localConfig = ref(null)
const initialPayloadSignature = ref('')
const form = reactive({ provider: '', mainModel: '', liteModel: '', codingModel: '', allowDataSamples: false, temperature: null, maxTokens: null, topP: null })

const config = computed(() => localConfig.value)
const hasOverrides = computed(() => Object.entries(config.value?.overrides || {}).some(([key, value]) => key !== 'allow_llm_data_samples' && value !== null && value !== ''))
const useDefaults = ref(true)
const providerOptions = computed(() => (preferencesStore.availableProviders || []).map((value) => ({ value, label: value === 'openrouter' ? 'OpenRouter' : value === 'openai' ? 'OpenAI' : value === 'ollama' ? 'Ollama (local)' : value })))
const modelOptions = (values) => (Array.isArray(values) ? values : []).map((value) => ({ value, label: value }))
const mainModelOptions = computed(() => modelOptions(providerCatalog.value?.provider_available_main_models || preferencesStore.providerMainModels))
const liteModelOptions = computed(() => modelOptions(providerCatalog.value?.provider_available_lite_models || preferencesStore.providerLiteModels))
const codingModelOptions = computed(() => mainModelOptions.value)
const effectiveSummary = computed(() => {
  const effective = config.value?.effective
  if (!effective) return 'Loading effective models…'
  return `${effective.provider} · ${effective.main_model || 'Main model required'} · ${effective.lite_model || 'Lite model required'} · ${effective.coding_model || 'Coding model required'}`
})
const credentialLabel = computed(() => config.value?.readiness?.credential_ready ? 'Using application credential' : 'Application credential required')
const isDirty = computed(() => Boolean(config.value) && payloadSignature(buildPayload()) !== initialPayloadSignature.value)

watch(config, hydrate, { immediate: true })
watch(() => workspaceStore.workspaceAIConfig, (value) => {
  if (props.workspaceId === workspaceStore.activeWorkspaceId && value) localConfig.value = value
})
watch(() => props.workspaceId, async (workspaceId) => {
  localConfig.value = null
  initialPayloadSignature.value = ''
  saveStateLabel.value = 'Changes apply to this workspace only.'
  if (workspaceId) localConfig.value = await workspaceStore.fetchWorkspaceAIConfig(workspaceId)
}, { immediate: true })

function hydrate(value) {
  if (!value) return
  const overrides = value.overrides || {}
  const effective = value.effective || {}
  useDefaults.value = !Object.entries(overrides).some(([key, item]) => key !== 'allow_llm_data_samples' && item !== null && item !== '')
  form.provider = overrides.provider || effective.provider || ''
  form.mainModel = overrides.main_model || effective.main_model || ''
  form.liteModel = overrides.lite_model || effective.lite_model || ''
  form.codingModel = overrides.coding_model || effective.coding_model || ''
  form.allowDataSamples = Boolean(overrides.allow_llm_data_samples)
  form.temperature = overrides.temperature
  form.maxTokens = overrides.max_tokens
  form.topP = overrides.top_p
  initialPayloadSignature.value = payloadSignature(buildPayload())
  errorMessage.value = ''
  if (form.provider) loadProviderModels(form.provider)
}

async function loadProviderModels(provider) {
  try { providerCatalog.value = await preferencesApi.get(provider) } catch (_error) { providerCatalog.value = null }
}

function buildPayload() {
  return {
    llm_provider_override: useDefaults.value ? null : form.provider,
    main_model_override: useDefaults.value ? null : form.mainModel,
    lite_model_override: useDefaults.value ? null : form.liteModel,
    coding_model_override: useDefaults.value ? null : form.codingModel,
    llm_temperature_override: useDefaults.value ? null : (form.temperature === '' ? null : form.temperature),
    llm_max_tokens_override: useDefaults.value ? null : (form.maxTokens === '' ? null : form.maxTokens),
    llm_top_p_override: useDefaults.value ? null : (form.topP === '' ? null : form.topP),
    allow_llm_data_samples: Boolean(form.allowDataSamples),
  }
}

function payloadSignature(payload) {
  return JSON.stringify(payload)
}

async function save() {
  isSaving.value = true
  errorMessage.value = ''
  try {
    const savedConfig = await workspaceStore.saveWorkspaceAIConfig(buildPayload(), props.workspaceId)
    localConfig.value = savedConfig
    hydrate(savedConfig)
    saveStateLabel.value = 'Saved.'
  } catch (error) { errorMessage.value = error?.message || 'Could not save AI settings.' } finally { isSaving.value = false }
}
</script>
