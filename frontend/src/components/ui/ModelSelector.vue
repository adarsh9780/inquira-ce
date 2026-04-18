<template>
  <div class="relative">
    <Listbox v-model="selectedModel" @update:model-value="handleModelChange">
      <div class="relative">
        <!-- Text-only trigger (Cursor-style: "Model Name ↓") -->
        <ListboxButton
          class="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-colors focus:outline-none group"
          style="color: var(--color-text-main); border-color: var(--color-border); background-color: color-mix(in srgb, var(--color-surface) 88%, var(--color-workspace-surface));"
          title="Select model"
        >
          <span class="truncate max-w-[170px]" style="color: var(--color-text-main);">
            {{ getModelDisplayName(selectedModel) }}
          </span>
          <ChevronDownIcon class="h-3.5 w-3.5 shrink-0 transition-transform group-data-[open]:rotate-180" style="color: var(--color-text-muted);" />
        </ListboxButton>

        <transition
          enter-active-class="transition duration-100 ease-out"
          enter-from-class="opacity-0 scale-95 translate-y-1"
          enter-to-class="opacity-100 scale-100 translate-y-0"
          leave-active-class="transition duration-75 ease-in"
          leave-from-class="opacity-100"
          leave-to-class="opacity-0"
        >
          <ListboxOptions
            class="absolute z-50 bottom-full mb-2 right-0 min-w-[200px] rounded-lg py-1 text-xs shadow-md focus:outline-none overflow-hidden"
            style="background-color: var(--color-workspace-surface); border: 1px solid var(--color-border);"
          >
            <div class="px-2 pb-1 pt-1">
              <input
                v-model="searchQuery"
                type="text"
                class="w-full rounded-md border px-2 py-1 text-[12px] focus:outline-none"
                placeholder="Search model"
                style="background-color: var(--color-base); border-color: var(--color-border); color: var(--color-text-main);"
                @click.stop
                @keydown.stop
              />
            </div>
            <div v-if="backendLoading && searchQuery" class="px-3 pb-1 text-[11px]" style="color: var(--color-text-muted);">
              Searching...
            </div>
            <ListboxOption
              v-slot="{ active, selected }"
              v-for="model in filteredModels"
              :key="model.value"
              :value="model.value"
              as="template"
            >
              <li
                :style="{
                  backgroundColor: active ? 'color-mix(in srgb, var(--color-surface) 78%, transparent)' : 'transparent',
                  color: 'var(--color-text-main)'
                }"
                class="relative cursor-default select-none py-2 pl-3 pr-9 flex items-center justify-between"
              >
                <span :class="selected ? 'font-semibold' : 'font-normal'" class="block truncate">
                  {{ model.label }}
                </span>
                <span v-if="selected" class="absolute right-3 flex items-center">
                  <CheckIcon class="h-4 w-4" style="color: var(--color-text-muted);" aria-hidden="true" />
                </span>
              </li>
            </ListboxOption>
            <li
              v-if="!backendLoading && filteredModels.length === 0"
              class="px-3 py-2 text-[11px]"
              style="color: var(--color-text-muted);"
            >
              No models found.
            </li>
          </ListboxOptions>
        </transition>
      </div>
    </Listbox>
  </div>
</template>

<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import {
  Listbox,
  ListboxButton,
  ListboxOptions,
  ListboxOption,
} from '@headlessui/vue'
import { CheckIcon, ChevronDownIcon } from '@heroicons/vue/20/solid'
import {
  mergeModelOptions,
  normalizeModelOptions,
  optionMatchesSearch,
  prettifyModelName,
} from './modelDropdownUtils'

const props = defineProps({
  selectedModel: {
    type: String,
    required: true
  },
  provider: {
    type: String,
    default: '',
  },
  modelOptions: {
    type: Array,
    default: () => []
  },
  backendSearch: {
    type: Function,
    default: null,
  },
  searchLoading: {
    type: Boolean,
    default: false,
  },
  backendSearchLimit: {
    type: Number,
    default: 25,
  },
  backendSearchMinChars: {
    type: Number,
    default: 3,
  },
  searchDebounceMs: {
    type: Number,
    default: 250,
  },
  backendSearchDebounceMs: {
    type: Number,
    default: 250,
  },
  maxOptionsWithoutSearch: {
    type: Number,
    default: 10
  }
})

const emit = defineEmits(['model-changed'])

const selectedModel = ref(props.selectedModel)
const searchQuery = ref('')
const backendModels = ref([])
const backendLoadingLocal = ref(false)
let backendSearchTimer = null
let backendSearchToken = 0

const fallbackModels = [
  'google/gemini-3-flash-preview',
  'google/gemini-2.5-flash',
  'google/gemini-2.5-flash-lite',
  'openrouter/free'
]

const availableModels = computed(() => {
  const source = Array.isArray(props.modelOptions) && props.modelOptions.length
    ? props.modelOptions
    : fallbackModels
  return normalizeModelOptions(source, props.provider)
})

const backendLoading = computed(() => Boolean(props.searchLoading) || backendLoadingLocal.value)

const filteredModels = computed(() => {
  const query = String(searchQuery.value || '').trim().toLowerCase()
  const source = availableModels.value
  if (!query) {
    const limit = Number(props.maxOptionsWithoutSearch || 0)
    if (limit > 0) return source.slice(0, limit)
    return source
  }
  const localMatches = source.filter((model) => optionMatchesSearch(model, query))
  if (!shouldSearchBackend(query, localMatches)) {
    return localMatches
  }
  return mergeModelOptions(localMatches, backendModels.value)
})

watch(
  () => props.selectedModel,
  (next) => {
    selectedModel.value = next
  }
)

watch(searchQuery, (value) => {
  scheduleBackendSearch(String(value || '').trim())
})

watch(
  () => props.backendSearch,
  () => {
    backendModels.value = []
    scheduleBackendSearch(String(searchQuery.value || '').trim())
  }
)

onBeforeUnmount(() => {
  if (backendSearchTimer) clearTimeout(backendSearchTimer)
})

function handleModelChange(value) {
  selectedModel.value = value
  searchQuery.value = ''
  backendModels.value = []
  emit('model-changed', value)
}

function getModelDisplayName(modelValue) {
  const model = availableModels.value.find(m => m.value === modelValue)
  return model ? model.label : prettifyModelName(modelValue)
}

function shouldSearchBackend(query, localMatches) {
  const normalizedQuery = String(query || '').trim().toLowerCase()
  if (typeof props.backendSearch !== 'function') return false
  if (normalizedQuery.length < Number(props.backendSearchMinChars || 3)) return false
  return !localMatches.some((model) => {
    const value = String(model?.value || '').trim().toLowerCase()
    const label = String(model?.label || '').trim().toLowerCase()
    return value === normalizedQuery || label === normalizedQuery
  })
}

function scheduleBackendSearch(query) {
  if (backendSearchTimer) clearTimeout(backendSearchTimer)
  if (!query || typeof props.backendSearch !== 'function') {
    backendModels.value = []
    backendLoadingLocal.value = false
    return
  }

  const localMatches = availableModels.value.filter((model) => optionMatchesSearch(model, query))
  if (!shouldSearchBackend(query, localMatches)) {
    backendModels.value = []
    backendLoadingLocal.value = false
    return
  }

  const wait = Number(props.searchDebounceMs ?? props.backendSearchDebounceMs ?? 250)
  backendSearchTimer = setTimeout(() => {
    void runBackendSearch(query)
  }, Number.isFinite(wait) && wait >= 0 ? wait : 250)
}

async function runBackendSearch(query) {
  const token = ++backendSearchToken
  backendLoadingLocal.value = true
  try {
    const result = await props.backendSearch(query, Number(props.backendSearchLimit || 25))
    if (token !== backendSearchToken) return
    const raw = Array.isArray(result)
      ? result
      : Array.isArray(result?.models)
        ? result.models
        : []
    backendModels.value = normalizeModelOptions(raw, props.provider)
  } catch (_error) {
    if (token === backendSearchToken) {
      backendModels.value = []
    }
  } finally {
    if (token === backendSearchToken) {
      backendLoadingLocal.value = false
    }
  }
}
</script>
