<template>
  <section class="border-t border-[var(--color-border)] pt-4">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h4 class="section-label">AI configuration</h4>
        <p class="mt-1 text-xs text-[var(--color-text-muted)]">{{ effectiveSummary }}</p>
      </div>
      <button type="button" class="text-xs font-semibold text-[var(--color-accent)] hover:underline" @click="isEditing = !isEditing">{{ isEditing ? 'Done' : 'Customize' }}</button>
    </div>

    <div class="mt-3 flex items-center gap-2 text-[11px] text-[var(--color-text-muted)]">
      <span class="h-1.5 w-1.5 rounded-full" :class="config?.readiness?.credential_ready ? 'bg-[var(--color-success)]' : 'bg-[var(--color-warning)]'"></span>
      <span>{{ credentialLabel }}</span>
      <span aria-hidden="true">·</span>
      <span>{{ hasOverrides ? 'Workspace override' : 'Application defaults' }}</span>
    </div>

    <div v-if="isEditing" class="mt-4 space-y-5 border-t border-[var(--color-border)] pt-4">
      <label class="flex items-center justify-between gap-4">
        <span><span class="block text-sm font-medium text-[var(--color-text-main)]">Use application defaults</span><span class="mt-0.5 block text-xs text-[var(--color-text-muted)]">Keep model choices in sync with Models settings.</span></span>
        <input v-model="useDefaults" type="checkbox" class="h-4 w-4 accent-[var(--color-accent)]" @change="handleDefaultsChange" />
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
      </div>

      <label class="flex items-start gap-3 border-t border-[var(--color-border)] pt-4">
        <input v-model="form.allowDataSamples" type="checkbox" class="mt-0.5 h-4 w-4 accent-[var(--color-accent)]" />
        <span><span class="block text-sm font-medium text-[var(--color-text-main)]">Allow bounded data samples in model prompts</span><span class="mt-1 block text-xs leading-relaxed text-[var(--color-text-muted)]">Off keeps row previews local. This permission applies only to this workspace.</span></span>
      </label>

      <details class="border-t border-[var(--color-border)] pt-4">
        <summary class="cursor-pointer text-xs font-semibold text-[var(--color-text-sub)]">Advanced generation controls</summary>
        <div class="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
          <label><span class="input-label">Temperature</span><input v-model.number="form.temperature" type="number" min="0" max="2" step="0.1" class="input-base input-outlined" placeholder="Default" /></label>
          <label><span class="input-label">Max tokens</span><input v-model.number="form.maxTokens" type="number" min="1" max="131072" class="input-base input-outlined" placeholder="Default" /></label>
          <label><span class="input-label">Top P</span><input v-model.number="form.topP" type="number" min="0" max="1" step="0.05" class="input-base input-outlined" placeholder="Default" /></label>
        </div>
      </details>

      <div class="flex items-center justify-between gap-3 border-t border-[var(--color-border)] pt-4">
        <p class="text-xs" :class="errorMessage ? 'text-[var(--color-danger)]' : 'text-[var(--color-text-muted)]'">{{ errorMessage || saveStateLabel }}</p>
        <button type="button" class="btn-primary px-4 py-2 text-xs" :disabled="isSaving" @click="save">{{ isSaving ? 'Saving…' : 'Save AI settings' }}</button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { apiService } from '../../../services/apiService'
import { useAppStore } from '../../../stores/appStore'
import HeaderDropdown from '../../ui/HeaderDropdown.vue'

const props = defineProps({ workspaceId: { type: String, required: true } })
const appStore = useAppStore()
const isEditing = ref(false)
const isSaving = ref(false)
const errorMessage = ref('')
const saveStateLabel = ref('Changes apply to this workspace only.')
const providerCatalog = ref(null)
const localConfig = ref(null)
const form = reactive({ provider: '', mainModel: '', liteModel: '', allowDataSamples: false, temperature: null, maxTokens: null, topP: null })

const config = computed(() => localConfig.value)
const hasOverrides = computed(() => Object.entries(config.value?.overrides || {}).some(([key, value]) => key !== 'allow_llm_data_samples' && value !== null && value !== ''))
const useDefaults = ref(true)
const providerOptions = computed(() => (appStore.availableProviders || []).map((value) => ({ value, label: value === 'openrouter' ? 'OpenRouter' : value === 'openai' ? 'OpenAI' : value === 'ollama' ? 'Ollama (local)' : value })))
const modelOptions = (values) => (Array.isArray(values) ? values : []).map((value) => ({ value, label: value }))
const mainModelOptions = computed(() => modelOptions(providerCatalog.value?.provider_available_main_models || appStore.providerMainModels))
const liteModelOptions = computed(() => modelOptions(providerCatalog.value?.provider_available_lite_models || appStore.providerLiteModels))
const effectiveSummary = computed(() => {
  const effective = config.value?.effective
  if (!effective) return 'Loading effective models…'
  return `${effective.provider} · ${effective.main_model || 'Main model required'} · ${effective.lite_model || 'Lite model required'}`
})
const credentialLabel = computed(() => config.value?.readiness?.credential_ready ? 'Using application credential' : 'Application credential required')

watch(config, hydrate, { immediate: true })
watch(() => appStore.workspaceAIConfig, (value) => {
  if (props.workspaceId === appStore.activeWorkspaceId && value) localConfig.value = value
})
watch(() => props.workspaceId, async (workspaceId) => {
  localConfig.value = null
  if (workspaceId) localConfig.value = await appStore.fetchWorkspaceAIConfig(workspaceId)
}, { immediate: true })

function hydrate(value) {
  if (!value) return
  const overrides = value.overrides || {}
  const effective = value.effective || {}
  useDefaults.value = !Object.entries(overrides).some(([key, item]) => key !== 'allow_llm_data_samples' && item !== null && item !== '')
  form.provider = overrides.provider || effective.provider || ''
  form.mainModel = overrides.main_model || effective.main_model || ''
  form.liteModel = overrides.lite_model || effective.lite_model || ''
  form.allowDataSamples = Boolean(overrides.allow_llm_data_samples)
  form.temperature = overrides.temperature
  form.maxTokens = overrides.max_tokens
  form.topP = overrides.top_p
  if (form.provider) loadProviderModels(form.provider)
}

async function loadProviderModels(provider) {
  try { providerCatalog.value = await apiService.v1GetPreferences(provider) } catch (_error) { providerCatalog.value = null }
}

async function handleDefaultsChange() {
  if (!useDefaults.value) return
  isSaving.value = true
  try { localConfig.value = await appStore.resetWorkspaceAIConfig(props.workspaceId); saveStateLabel.value = 'Using application defaults.' } catch (error) { errorMessage.value = error?.message || 'Could not reset AI settings.' } finally { isSaving.value = false }
}

async function save() {
  isSaving.value = true
  errorMessage.value = ''
  try {
    localConfig.value = await appStore.saveWorkspaceAIConfig({
      llm_provider_override: useDefaults.value ? null : form.provider,
      main_model_override: useDefaults.value ? null : form.mainModel,
      lite_model_override: useDefaults.value ? null : form.liteModel,
      llm_temperature_override: useDefaults.value ? null : (form.temperature === '' ? null : form.temperature),
      llm_max_tokens_override: useDefaults.value ? null : (form.maxTokens === '' ? null : form.maxTokens),
      llm_top_p_override: useDefaults.value ? null : (form.topP === '' ? null : form.topP),
      allow_llm_data_samples: Boolean(form.allowDataSamples),
    }, props.workspaceId)
    saveStateLabel.value = 'Saved.'
  } catch (error) { errorMessage.value = error?.message || 'Could not save AI settings.' } finally { isSaving.value = false }
}
</script>
