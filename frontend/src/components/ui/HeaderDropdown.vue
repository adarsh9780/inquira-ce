<template>
  <div class="relative" :class="maxWidthClass" :style="containerStyle">
    <Listbox v-slot="{ open }" :model-value="modelValue" @update:model-value="handleChange">
      <div class="relative">
        <ListboxButton
          ref="triggerRef"
          class="inline-flex w-full items-center justify-between gap-2 rounded-md border px-2.5 py-1 text-[13px] font-medium transition-colors focus:outline-none"
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
              <div v-if="backendLoading && searchable && searchQuery" class="px-3 pb-1 text-[11px]" :style="dropdownMutedTextStyle">
                Searching...
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
                        :class="[dropdownOptionClass, 'pl-3 pr-9']"
                      >
                        <span :class="selected ? 'font-semibold' : 'font-normal'" class="block truncate pr-2" :title="option.label">
                          {{ option.label }}
                        </span>
                        <span v-if="selected" class="absolute right-2.5 top-1/2 -translate-y-1/2">
                          <CheckIcon class="h-4 w-4" style="color: var(--color-text-muted);" />
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
                      :class="[dropdownOptionClass, 'pl-3 pr-9']"
                    >
                      <span :class="selected ? 'font-semibold' : 'font-normal'" class="block truncate pr-2" :title="option.label">
                        {{ option.label }}
                      </span>
                      <span v-if="selected" class="absolute right-2.5 top-1/2 -translate-y-1/2">
                        <CheckIcon class="h-4 w-4" style="color: var(--color-text-muted);" />
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
  mergeModelOptions,
  normalizeModelOptions,
  optionMatchesSearch as matchesModelOptionSearch,
  providerLabel as sharedProviderLabel,
} from './modelDropdownUtils'
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
    type: [String, Number, null],
    default: null
  },
  options: {
    type: Array,
    default: () => []
  },
  placeholder: {
    type: String,
    default: 'Select'
  },
  ariaLabel: {
    type: String,
    default: 'Select option'
  },
  maxWidthClass: {
    type: String,
    default: 'max-w-[220px]'
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
  backendSearch: {
    type: Function,
    default: null,
  },
  backendSearchLimit: {
    type: Number,
    default: 25,
  },
  backendSearchMinChars: {
    type: Number,
    default: 3,
  },
  backendSearchDebounceMs: {
    type: Number,
    default: 250,
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
  },
  maxOptionsWithoutSearch: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['update:modelValue'])
const searchQuery = ref('')
const backendOptions = ref([])
const backendLoading = ref(false)
const triggerRef = ref(null)
const optionsRef = ref(null)
const floatingOptionsStyle = ref({
  left: '0px',
  top: '0px',
  width: '0px',
  maxHeight: '240px',
  ...dropdownSurfaceStyle(),
})
let backendSearchTimer = null
let backendSearchToken = 0

const normalizedOptions = computed(() => normalizeModelOptions(props.options))
const selectedOption = computed(() => normalizedOptions.value.find((option) => option.value === props.modelValue) ?? null)
const selectedLabel = computed(() => selectedOption.value?.label || props.placeholder)
const hasSelection = computed(() => !!selectedOption.value)
const normalizedSearchQuery = computed(() => String(searchQuery.value || '').trim().toLowerCase())
const filteredOptions = computed(() => {
  const options = normalizedOptions.value
  const query = normalizedSearchQuery.value
  if (!query) {
    const maxCount = Number(props.maxOptionsWithoutSearch || 0)
    if (maxCount > 0) {
      return options.slice(0, maxCount)
    }
    return options
  }
  const localMatches = options.filter((option) => matchesModelOptionSearch(option, query))
  if (!shouldSearchBackend(query, localMatches)) {
    return localMatches
  }
  return mergeModelOptions(localMatches, backendOptions.value)
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
    label: sharedProviderLabel(key),
    options
  }))
})
const maxLabelChars = computed(() => {
  const optionChars = props.options.reduce((maxChars, option) => {
    const label = String(option?.label || '')
    return Math.max(maxChars, label.length)
  }, 0)
  return Math.max(optionChars, String(props.placeholder || '').length)
})
const containerStyle = computed(() => {
  if (!props.fitToLongestLabel) return null
  const desiredChars = maxLabelChars.value + 5 // icon + horizontal padding
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

watch(searchQuery, (value) => {
  scheduleBackendSearch(String(value || '').trim())
})

watch(
  () => props.backendSearch,
  () => {
    backendOptions.value = []
    scheduleBackendSearch(String(searchQuery.value || '').trim())
  }
)

function handleChange(value) {
  if (props.searchable) {
    searchQuery.value = ''
    backendOptions.value = []
  }
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

function shouldSearchBackend(query, localMatches) {
  if (typeof props.backendSearch !== 'function') return false
  if (query.length < Number(props.backendSearchMinChars || 3)) return false
  return localMatches.length === 0
}

function scheduleBackendSearch(query) {
  if (backendSearchTimer) clearTimeout(backendSearchTimer)
  if (!query || typeof props.backendSearch !== 'function') {
    backendOptions.value = []
    backendLoading.value = false
    return
  }

  const localMatches = normalizedOptions.value.filter((option) => matchesModelOptionSearch(option, query))
  if (!shouldSearchBackend(query, localMatches)) {
    backendOptions.value = []
    backendLoading.value = false
    return
  }

  const wait = Number(props.backendSearchDebounceMs || 250)
  backendSearchTimer = setTimeout(() => {
    void runBackendSearch(query)
  }, Number.isFinite(wait) && wait >= 0 ? wait : 250)
}

async function runBackendSearch(query) {
  const token = ++backendSearchToken
  backendLoading.value = true
  try {
    const result = await props.backendSearch(query, Number(props.backendSearchLimit || 25))
    if (token !== backendSearchToken) return
    const raw = Array.isArray(result)
      ? result
      : Array.isArray(result?.models)
        ? result.models
        : []
    backendOptions.value = normalizeModelOptions(raw)
  } catch (_error) {
    if (token === backendSearchToken) {
      backendOptions.value = []
    }
  } finally {
    if (token === backendSearchToken) {
      backendLoading.value = false
    }
  }
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
  if (backendSearchTimer) clearTimeout(backendSearchTimer)
  unbindPositionListeners()
})

function optionKey(option, fallbackIndex, prefix = '') {
  const keyPrefix = prefix ? `${prefix}:` : ''
  if (option?.key != null) return `${keyPrefix}${String(option.key)}`
  if (option?.value != null) return `${keyPrefix}${String(option.value)}`
  return `${keyPrefix}${String(fallbackIndex)}`
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
</script>
