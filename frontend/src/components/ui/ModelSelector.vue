<template>
  <div class="relative">
    <Listbox v-model="selectedModel" @update:model-value="handleModelChange">
      <div class="relative">
        <ListboxButton
          class="relative w-48 cursor-default rounded-md bg-white py-2 pl-3 pr-10 text-left border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
        >
          <span class="flex items-center">
            <span class="block truncate">{{ getModelDisplayName(selectedModel) }}</span>
          </span>
          <span class="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
            <ChevronUpDownIcon class="h-5 w-5 text-gray-400" aria-hidden="true" />
          </span>
        </ListboxButton>

        <transition
          leave-active-class="transition duration-100 ease-in"
          leave-from-class="opacity-100"
          leave-to-class="opacity-0"
        >
          <ListboxOptions
            class="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm"
          >
            <ListboxOption
              v-slot="{ active, selected }"
              v-for="model in availableModels"
              :key="model.value"
              :value="model.value"
              as="template"
            >
              <li
                :class="[
                  active ? 'bg-blue-100 text-blue-900' : 'text-gray-900',
                  'relative cursor-default select-none py-2 pl-3 pr-9'
                ]"
              >
                <div class="flex items-center">
                  <span
                    :class="[
                      selected ? 'font-semibold' : 'font-normal',
                      'block truncate'
                    ]"
                  >
                    {{ model.name }}
                  </span>
                </div>

                <span
                  v-if="selected"
                  :class="[
                    active ? 'text-blue-600' : 'text-blue-600',
                    'absolute inset-y-0 right-0 flex items-center pr-4'
                  ]"
                >
                  <CheckIcon class="h-5 w-5" aria-hidden="true" />
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
import { CheckIcon, ChevronUpDownIcon } from '@heroicons/vue/20/solid'

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
