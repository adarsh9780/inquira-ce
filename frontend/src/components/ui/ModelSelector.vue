<script setup lang="ts">
import { computed } from 'vue'
import HeaderDropdown from './HeaderDropdown.vue'
import { normalizeModelOptions, prettifyModelName } from './modelDropdownUtils'

interface ModelOption {
  value: string
  label: string
  provider?: string
}

const props = withDefaults(defineProps<{
  selectedModel: string
  provider?: string
  modelOptions?: Array<ModelOption | string>
  backendSearch?: ((query: string, limit: number) => Promise<unknown>) | null
  searchLoading?: boolean
  backendSearchLimit?: number
  backendSearchMinChars?: number
  searchDebounceMs?: number
  backendSearchDebounceMs?: number
  maxOptionsWithoutSearch?: number
}>(), {
  provider: '',
  modelOptions: () => [],
  backendSearch: null,
  searchLoading: false,
  backendSearchLimit: 25,
  backendSearchMinChars: 3,
  searchDebounceMs: 250,
  backendSearchDebounceMs: 250,
  maxOptionsWithoutSearch: 10,
})

const emit = defineEmits<{
  'model-changed': [value: string]
  'manage-models': []
}>()

const fallbackModels = [
  'google/gemini-3-flash-preview',
  'google/gemini-2.5-flash',
  'google/gemini-2.5-flash-lite',
  'openrouter/free',
]

const availableModels = computed<ModelOption[]>(() => {
  const source = props.modelOptions.length ? props.modelOptions : fallbackModels
  return normalizeModelOptions(source, props.provider) as ModelOption[]
})

const selectedLabel = computed(() => {
  const model = availableModels.value.find((option) => option.value === props.selectedModel)
  return model?.label || prettifyModelName(props.selectedModel)
})

function handleModelChange(value: string | number | null) {
  if (value != null) emit('model-changed', String(value))
}
</script>

<template>
  <div class="relative w-full min-w-0">
    <HeaderDropdown
      :model-value="selectedModel"
      :options="availableModels"
      :trigger-label="selectedLabel"
      :backend-search="backendSearch"
      :backend-search-limit="backendSearchLimit"
      :backend-search-min-chars="backendSearchMinChars"
      :backend-search-debounce-ms="searchDebounceMs ?? backendSearchDebounceMs"
      :max-options-without-search="maxOptionsWithoutSearch"
      searchable
      search-placeholder="Search model"
      no-results-label="No models found."
      aria-label="Select model"
      max-width-class="w-full"
      :dropdown-min-width="288"
      @update:model-value="handleModelChange"
    >
      <template #footer>
        <button
          type="button"
          class="w-full rounded-md px-2 py-1.5 text-left text-[11px] font-semibold text-[var(--color-text-muted)] outline-none hover:bg-[var(--color-panel-muted)] hover:text-[var(--color-text-main)] focus-visible:ring-2 focus-visible:ring-[var(--color-focus-ring)]"
          @click.stop="emit('manage-models')"
        >
          Workspace model settings…
        </button>
      </template>
    </HeaderDropdown>
  </div>
</template>
