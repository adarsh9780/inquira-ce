<template>
  <div class="relative" :class="maxWidthClass" :style="containerStyle">
    <Listbox v-slot="{ open }" :model-value="modelValue" @update:model-value="handleChange" multiple>
      <div class="relative">
        <ListboxButton
          ref="triggerRef"
          class="inline-flex w-full items-center justify-between gap-2 rounded-md border px-2.5 py-1.5 text-[13px] font-medium transition-colors focus:outline-none"
          :style="triggerStyle"
          :aria-label="ariaLabel"
        >
          <span class="truncate" :title="selectedLabel">{{ selectedLabel }}</span>
          <ChevronUpDownIcon class="h-3.5 w-3.5 shrink-0 opacity-70" />
        </ListboxButton>

        <Portal>
          <transition
            enter-active-class="transition duration-100 ease-out"
            enter-from-class="opacity-0 scale-95 -translate-y-1"
            enter-to-class="opacity-100 scale-100 translate-y-0"
            leave-active-class="transition duration-75 ease-in"
            leave-from-class="opacity-100"
            leave-to-class="opacity-0"
          >
            <ListboxOptions
              v-if="open"
              ref="optionsRef"
              :class="dropdownSurfaceClass"
              :style="floatingOptionsStyle"
            >
              <div
                v-if="searchable"
                :class="dropdownSearchRowClass"
                :style="dropdownSearchRowStyle"
              >
                <input
                  v-model="searchQuery"
                  type="text"
                  :class="dropdownSearchInputClass"
                  :placeholder="searchPlaceholder"
                  :style="dropdownSearchInputStyle"
                  @click.stop
                  @keydown.stop
                />
              </div>

              <template v-if="groupByProvider">
                <template v-if="groupedFilteredOptions.length">
                  <template v-for="group in groupedFilteredOptions" :key="group.key">
                    <div
                      :class="dropdownGroupLabelClass"
                      :style="dropdownMutedTextStyle"
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
                        :style="dropdownOptionStyle(active)"
                        :class="[dropdownOptionClass, 'pl-8 pr-4']"
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
                  :class="dropdownEmptyClass"
                  :style="dropdownMutedTextStyle"
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
                      :style="dropdownOptionStyle(active)"
                      :class="[dropdownOptionClass, 'pl-8 pr-4']"
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
                  :class="dropdownEmptyClass"
                  :style="dropdownMutedTextStyle"
                >
                  {{ noResultsLabel }}
                </div>
              </template>
            </ListboxOptions>
          </transition>
        </Portal>
      </div>
    </Listbox>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { Listbox, ListboxButton, ListboxOption, ListboxOptions, Portal } from '@headlessui/vue'
import { CheckIcon, ChevronUpDownIcon } from '@heroicons/vue/20/solid'
import {
  dropdownEmptyClass,
  dropdownGroupLabelClass,
  dropdownMutedTextStyle,
  dropdownOptionClass,
  dropdownOptionStyle,
  dropdownSearchInputClass,
  dropdownSearchInputStyle,
  dropdownSearchRowClass,
  dropdownSearchRowStyle,
  dropdownSurfaceClass,
  dropdownSurfaceStyle,
} from './dropdownShared'
import { updateFloatingDropdownPosition } from '../../composables/useFloatingDropdown'

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
const triggerRef = ref(null)
const optionsRef = ref(null)
const floatingOptionsStyle = ref({
  left: '0px',
  top: '0px',
  width: '0px',
  maxHeight: '240px',
  ...dropdownSurfaceStyle(),
})

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

function updateFloatingPosition() {
  const nextStyle = updateFloatingDropdownPosition(triggerRef)
  if (nextStyle) floatingOptionsStyle.value = nextStyle
}

function bindPositionListeners() {
  window.addEventListener('resize', updateFloatingPosition)
  window.addEventListener('scroll', updateFloatingPosition, true)
}

function unbindPositionListeners() {
  window.removeEventListener('resize', updateFloatingPosition)
  window.removeEventListener('scroll', updateFloatingPosition, true)
}

watch(optionsRef, async (value) => {
  if (!value) return
  await nextTick()
  updateFloatingPosition()
})

watch(triggerRef, (value) => {
  if (!value) return
  updateFloatingPosition()
})

watch(searchQuery, () => {
  nextTick(() => updateFloatingPosition())
})

watch(filteredOptions, () => {
  nextTick(() => updateFloatingPosition())
})

watch(groupedFilteredOptions, () => {
  nextTick(() => updateFloatingPosition())
})

watch(optionsRef, (value) => {
  if (value) {
    bindPositionListeners()
    return
  }
  unbindPositionListeners()
})

onBeforeUnmount(() => {
  unbindPositionListeners()
})

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
