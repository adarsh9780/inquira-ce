<template>
  <div class="relative">
    <Listbox v-model="selectedModel" @update:model-value="handleModelChange">
      <div class="relative">
        <!-- Text-only trigger (Cursor-style: "Model Name ↓") -->
        <ListboxButton
          class="flex items-center gap-1 text-sm font-medium transition-colors focus:outline-none group"
          style="color: var(--color-text-muted);"
        >
          <span class="truncate max-w-[160px]" style="color: var(--color-text-main);">
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
            class="absolute z-50 bottom-full mb-2 right-0 min-w-[200px] rounded-xl py-1 text-sm shadow-xl ring-1 ring-black/5 focus:outline-none overflow-hidden"
            style="background-color: var(--color-surface); border: 1px solid var(--color-border);"
          >
            <ListboxOption
              v-slot="{ active, selected }"
              v-for="model in availableModels"
              :key="model.value"
              :value="model.value"
              as="template"
            >
              <li
                :style="{
                  backgroundColor: active ? 'color-mix(in srgb, var(--color-text-main) 6%, transparent)' : 'transparent',
                  color: 'var(--color-text-main)'
                }"
                class="relative cursor-default select-none py-2 pl-3 pr-9 flex items-center justify-between"
              >
                <span :class="selected ? 'font-semibold' : 'font-normal'" class="block truncate">
                  {{ model.name }}
                </span>
                <span v-if="selected" class="absolute right-3 flex items-center">
                  <CheckIcon class="h-4 w-4" style="color: var(--color-text-muted);" aria-hidden="true" />
                </span>
              </li>
            </ListboxOption>
          </ListboxOptions>
        </transition>
      </div>
    </Listbox>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import {
  Listbox,
  ListboxButton,
  ListboxOptions,
  ListboxOption,
} from '@headlessui/vue'
import { CheckIcon, ChevronDownIcon } from '@heroicons/vue/20/solid'

const props = defineProps({
  selectedModel: {
    type: String,
    required: true
  },
  modelOptions: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['model-changed'])

const selectedModel = ref(props.selectedModel)

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
  return source.map((value) => ({
    value,
    name: prettifyModelName(value)
  }))
})

watch(
  () => props.selectedModel,
  (next) => {
    selectedModel.value = next
  }
)

function handleModelChange(value) {
  selectedModel.value = value
  emit('model-changed', value)
}

function getModelDisplayName(modelValue) {
  const model = availableModels.value.find(m => m.value === modelValue)
  return model ? model.name : prettifyModelName(modelValue)
}

function prettifyModelName(modelId) {
  const raw = String(modelId || '').trim()
  if (!raw) return ''
  if (raw === 'openrouter/free') return 'OpenRouter Free'
  const withoutVendor = raw.includes('/') ? raw.split('/').slice(1).join('/') : raw
  return withoutVendor
    .split('-')
    .filter(Boolean)
    .map((part) => part.toUpperCase() === 'GPT' ? 'GPT' : `${part.charAt(0).toUpperCase()}${part.slice(1)}`)
    .join(' ')
}
</script>
