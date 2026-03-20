<template>
  <div class="relative" :class="maxWidthClass" :style="containerStyle">
    <Listbox :model-value="modelValue" @update:model-value="handleChange" multiple>
      <div class="relative">
        <ListboxButton
          class="inline-flex w-full items-center justify-between gap-2 rounded-md border px-2.5 py-1.5 text-[13px] font-medium transition-colors focus:outline-none"
          :style="triggerStyle"
          :aria-label="ariaLabel"
        >
          <span class="truncate" :title="selectedLabel">{{ selectedLabel }}</span>
          <ChevronUpDownIcon class="h-3.5 w-3.5 shrink-0 opacity-70" />
        </ListboxButton>

        <transition
          enter-active-class="transition duration-100 ease-out"
          enter-from-class="opacity-0 scale-95 -translate-y-1"
          enter-to-class="opacity-100 scale-100 translate-y-0"
          leave-active-class="transition duration-75 ease-in"
          leave-from-class="opacity-100"
          leave-to-class="opacity-0"
        >
          <ListboxOptions
            class="absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-md py-1 shadow-md focus:outline-none"
            style="background-color: var(--color-surface); border: 1px solid var(--color-border);"
          >
            <div v-if="searchable" class="px-2 pb-1">
              <input
                v-model="searchQuery"
                type="text"
                class="w-full rounded-md border px-2 py-1 text-[12px] focus:outline-none"
                :placeholder="searchPlaceholder"
                style="background-color: var(--color-base); border-color: var(--color-border); color: var(--color-text-main);"
                @click.stop
                @keydown.stop
              />
            </div>

            <template v-if="groupByProvider">
              <template v-if="groupedFilteredOptions.length">
                <template v-for="group in groupedFilteredOptions" :key="group.key">
                  <div
                    class="px-3 py-1 text-[11px] font-semibold uppercase tracking-wide"
                    style="color: var(--color-text-muted);"
                  >
                    {{ group.label }}
                  </div>
                  <ListboxOption
                    v-for="(option, index) in group.options"
                    :key="optionKey(option, index, group.key)"
                    v-slot="{ active, selected }"
                    :value="option.value"
                    as="template"
                  >
                    <li
                      :style="{
                        backgroundColor: active ? 'color-mix(in srgb, var(--color-text-main) 6%, transparent)' : 'transparent',
                        color: 'var(--color-text-main)'
                      }"
                      class="relative cursor-default select-none py-2 pl-8 pr-4 text-[13px]"
                    >
                      <span v-if="selected" class="absolute left-2.5 top-1/2 -translate-y-1/2">
                        <CheckIcon class="h-4 w-4" style="color: var(--color-text-muted);" />
                      </span>
                      <span :class="selected ? 'font-semibold' : 'font-normal'" class="block truncate" :title="option.label">
                        {{ option.label }}
                      </span>
                    </li>
                  </ListboxOption>
                </template>
              </template>
              <div
                v-else
                class="px-3 py-2 text-[12px]"
                style="color: var(--color-text-muted);"
              >
                {{ noResultsLabel }}
              </div>
            </template>

            <template v-else>
              <template v-if="filteredOptions.length">
                <ListboxOption
                  v-for="(option, index) in filteredOptions"
                  :key="optionKey(option, index)"
                  v-slot="{ active, selected }"
                  :value="option.value"
                  as="template"
                >
                  <li
                    :style="{
                      backgroundColor: active ? 'color-mix(in srgb, var(--color-text-main) 6%, transparent)' : 'transparent',
                      color: 'var(--color-text-main)'
                    }"
                    class="relative cursor-default select-none py-2 pl-8 pr-4 text-[13px]"
                  >
                    <span v-if="selected" class="absolute left-2.5 top-1/2 -translate-y-1/2">
                      <CheckIcon class="h-4 w-4" style="color: var(--color-text-muted);" />
                    </span>
                    <span :class="selected ? 'font-semibold' : 'font-normal'" class="block truncate" :title="option.label">
                      {{ option.label }}
                    </span>
                  </li>
                </ListboxOption>
              </template>
              <div
                v-else
                class="px-3 py-2 text-[12px]"
                style="color: var(--color-text-muted);"
              >
                {{ noResultsLabel }}
              </div>
            </template>
          </ListboxOptions>
        </transition>
      </div>
    </Listbox>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { Listbox, ListboxButton, ListboxOption, ListboxOptions } from '@headlessui/vue'
import { CheckIcon, ChevronUpDownIcon } from '@heroicons/vue/20/solid'

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => []
  },
  options: {
    type: Array,
    default: () => []
  },
  placeholder: {
    type: String,
    default: 'Select options'
  },
  ariaLabel: {
    type: String,
    default: 'Select options'
  },
  maxWidthClass: {
    type: String,
    default: 'max-w-md'
  },
  fitToLongestLabel: {
    type: Boolean,
    default: false
  },
  minChars: {
    type: Number,
    default: 24
  },
  maxChars: {
    type: Number,
    default: 52
  },
  searchable: {
    type: Boolean,
    default: false
  },
  searchPlaceholder: {
    type: String,
    default: 'Search models'
  },
  groupByProvider: {
    type: Boolean,
    default: false
  },
  noResultsLabel: {
    type: String,
    default: 'No results found'
  }
})

const emit = defineEmits(['update:modelValue'])
const searchQuery = ref('')

const selectedOptions = computed(() => {
  if (!Array.isArray(props.modelValue)) return []
  return props.options.filter((option) => props.modelValue.includes(option.value))
})

const selectedLabel = computed(() => {
  if (selectedOptions.value.length === 0) return props.placeholder
  if (selectedOptions.value.length === 1) return selectedOptions.value[0].label
  if (selectedOptions.value.length === props.options.length && props.options.length > 0) return 'All Models Selected'
  return `${selectedOptions.value.length} selected`
})

const hasSelection = computed(() => selectedOptions.value.length > 0)
const normalizedSearchQuery = computed(() => String(searchQuery.value || '').trim().toLowerCase())
const filteredOptions = computed(() => {
  const options = Array.isArray(props.options) ? props.options : []
  const query = normalizedSearchQuery.value
  if (!query) return options
  return options.filter((option) => optionMatchesSearch(option, query))
})
const groupedFilteredOptions = computed(() => {
  const groups = new Map()
  filteredOptions.value.forEach((option) => {
    const providerKey = normalizeProviderKey(resolveProvider(option))
    if (!groups.has(providerKey)) {
      groups.set(providerKey, [])
    }
    groups.get(providerKey).push(option)
  })
  return Array.from(groups.entries()).map(([key, options]) => ({
    key,
    label: formatProviderLabel(key),
    options
  }))
})

const maxLabelChars = computed(() => {
  const optionChars = props.options.reduce((maxChars, option) => {
    const label = String(option?.label || '')
    return Math.max(maxChars, label.length)
  }, 0)
  return Math.max(optionChars, String(props.placeholder || '').length, 20) // min 20 for "X items selected"
})

const containerStyle = computed(() => {
  if (!props.fitToLongestLabel) return null
  const desiredChars = maxLabelChars.value + 5 // icon + padding
  const widthChars = Math.min(Math.max(desiredChars, Number(props.minChars || 24)), Number(props.maxChars || 52))
  return {
    width: `${widthChars}ch`,
    maxWidth: '100%'
  }
})

const triggerStyle = computed(() => ({
  color: hasSelection.value ? 'var(--color-text-main)' : 'var(--color-text-muted)',
  backgroundColor: 'var(--color-surface)',
  borderColor: 'var(--color-border)'
}))

function handleChange(value) {
  emit('update:modelValue', value)
}

function optionKey(option, fallbackIndex, prefix = '') {
  const keyPrefix = prefix ? `${prefix}:` : ''
  if (option?.key != null) return `${keyPrefix}${String(option.key)}`
  if (option?.value != null) return `${keyPrefix}${String(option.value)}`
  return `${keyPrefix}${String(fallbackIndex)}`
}

function optionMatchesSearch(option, query) {
  const normalized = String(query || '').trim().toLowerCase()
  if (!normalized) return true
  const provider = resolveProvider(option)
  const fields = [
    option?.label,
    option?.value,
    provider,
    formatProviderLabel(provider)
  ]
    .map((value) => String(value || '').toLowerCase())
    .filter(Boolean)
  return fields.some((field) => field.includes(normalized))
}

function resolveProvider(option) {
  const explicitProvider = String(option?.provider || '').trim()
  if (explicitProvider) return explicitProvider
  const rawValue = String(option?.value || '').trim()
  if (!rawValue.includes('/')) return ''
  return rawValue.split('/')[0].trim()
}

function normalizeProviderKey(provider) {
  const normalized = String(provider || '').trim().toLowerCase()
  return normalized || 'other'
}

function formatProviderLabel(provider) {
  const normalized = String(provider || '').trim().toLowerCase()
  if (!normalized || normalized === 'other') return 'Other'
  if (normalized === 'openai') return 'OpenAI'
  if (normalized === 'openrouter') return 'OpenRouter'
  if (normalized === 'anthropic') return 'Anthropic'
  if (normalized === 'google') return 'Google'
  if (normalized === 'ollama') return 'Ollama'
  return normalized
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map((part) => `${part.charAt(0).toUpperCase()}${part.slice(1)}`)
    .join(' ')
}
</script>
