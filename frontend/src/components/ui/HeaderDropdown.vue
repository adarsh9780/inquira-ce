<script setup lang="ts">
import {
  ComboboxAnchor,
  ComboboxContent,
  ComboboxEmpty,
  ComboboxInput,
  ComboboxItem,
  ComboboxItemIndicator,
  ComboboxPortal,
  ComboboxRoot,
  ComboboxTrigger,
  ComboboxViewport,
} from 'reka-ui'
import { CheckIcon, ChevronUpDownIcon } from '@heroicons/vue/20/solid'
import { computed, nextTick, onBeforeUnmount, ref, useId, watch, type Component } from 'vue'
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
  dropdownSearchInputClass,
  dropdownSearchInputStyle,
  dropdownSearchRowClass,
  dropdownSearchRowStyle,
  dropdownSurfaceClass,
  dropdownSurfaceStyle,
} from './dropdownShared'

type DropdownValue = string | number | null

interface DropdownOption {
  key?: string | number
  value: Exclude<DropdownValue, null>
  label: string
  icon?: Component
  provider?: string
}

const props = withDefaults(defineProps<{
  modelValue?: DropdownValue
  options?: DropdownOption[] | Array<string | number>
  placeholder?: string
  triggerLabel?: string
  ariaLabel?: string
  maxWidthClass?: string
  fitToLongestLabel?: boolean
  minChars?: number
  maxChars?: number
  searchable?: boolean
  backendSearch?: ((query: string, limit: number) => Promise<unknown>) | null
  backendSearchLimit?: number
  backendSearchMinChars?: number
  backendSearchDebounceMs?: number
  searchPlaceholder?: string
  groupByProvider?: boolean
  noResultsLabel?: string
  maxOptionsWithoutSearch?: number
  dropdownMinWidth?: number
  disabled?: boolean
}>(), {
  modelValue: null,
  options: () => [],
  placeholder: 'Select',
  triggerLabel: '',
  ariaLabel: 'Select option',
  maxWidthClass: 'max-w-[220px]',
  fitToLongestLabel: false,
  minChars: 24,
  maxChars: 52,
  searchable: false,
  backendSearch: null,
  backendSearchLimit: 25,
  backendSearchMinChars: 3,
  backendSearchDebounceMs: 250,
  searchPlaceholder: 'Search models',
  groupByProvider: false,
  noResultsLabel: 'No results found',
  maxOptionsWithoutSearch: 0,
  dropdownMinWidth: 0,
  disabled: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: DropdownValue]
}>()

const searchQuery = ref('')
const backendOptions = ref<DropdownOption[]>([])
const backendLoading = ref(false)
const isOpen = ref(false)
const triggerRef = ref<HTMLElement | null>(null)
const dropdownInstanceId = `header-dropdown-${useId()}`
const floatingOptionsStyle = computed<Record<string, string>>(() => ({
  width: 'var(--reka-combobox-trigger-width)',
  minWidth: props.dropdownMinWidth > 0 ? `${props.dropdownMinWidth}px` : '0px',
  maxHeight: 'min(240px, var(--reka-combobox-content-available-height))',
  visibility: isOpen.value ? 'visible' : 'hidden',
  ...dropdownSurfaceStyle(),
}))
let backendSearchTimer: ReturnType<typeof setTimeout> | null = null
let backendSearchToken = 0

const normalizedOptions = computed<DropdownOption[]>(() => normalizeModelOptions(props.options) as DropdownOption[])
const selectedOption = computed(() => normalizedOptions.value.find((option) => option.value === props.modelValue) ?? null)
const selectedLabel = computed(() => String(props.triggerLabel || '').trim() || selectedOption.value?.label || props.placeholder)
const hasSelection = computed(() => Boolean(selectedOption.value))
const normalizedSearchQuery = computed(() => String(searchQuery.value || '').trim().toLowerCase())
const filteredOptions = computed(() => {
  const options = normalizedOptions.value
  const query = normalizedSearchQuery.value
  if (!query) {
    return props.maxOptionsWithoutSearch > 0 ? options.slice(0, props.maxOptionsWithoutSearch) : options
  }
  const localMatches = options.filter((option) => matchesModelOptionSearch(option, query))
  return shouldSearchBackend(query, localMatches)
    ? mergeModelOptions(localMatches, backendOptions.value) as DropdownOption[]
    : localMatches
})
const groupedFilteredOptions = computed(() => {
  const groups = new Map<string, DropdownOption[]>()
  for (const option of filteredOptions.value) {
    const providerKey = normalizeProviderKey(resolveProvider(option))
    const options = groups.get(providerKey) || []
    options.push(option)
    groups.set(providerKey, options)
  }
  return [...groups.entries()].map(([key, options]) => ({
    key,
    label: sharedProviderLabel(key),
    options,
  }))
})
const maxLabelChars = computed(() => Math.max(
  ...normalizedOptions.value.map((option) => option.label.length),
  props.placeholder.length,
))
const containerStyle = computed(() => {
  if (!props.fitToLongestLabel) return undefined
  const widthChars = Math.min(Math.max(maxLabelChars.value + 5, props.minChars), props.maxChars)
  return { width: `${widthChars}ch`, maxWidth: '100%' }
})
const triggerStyle = computed(() => ({
  color: hasSelection.value ? 'var(--color-text-main)' : 'var(--color-text-muted)',
  backgroundColor: 'var(--color-surface)',
  borderColor: 'var(--color-border)',
}))

watch(searchQuery, (value) => scheduleBackendSearch(String(value || '').trim()))
watch(() => props.backendSearch, () => {
  backendOptions.value = []
  scheduleBackendSearch(String(searchQuery.value || '').trim())
})

function handleChange(value: DropdownValue) {
  searchQuery.value = ''
  backendOptions.value = []
  emit('update:modelValue', value)
}

function handleOpenChange(open: boolean) {
  isOpen.value = open
  if (open) {
    bindDismissListeners()
  } else {
    unbindDismissListeners()
    searchQuery.value = ''
  }
}

function dismissDropdown(restoreTriggerFocus = false) {
  if (!isOpen.value) return
  handleOpenChange(false)
  if (restoreTriggerFocus) {
    void nextTick(() => triggerRef.value?.focus())
  }
}

function eventPathContains(event: Event, element: Element | null) {
  return Boolean(element && event.composedPath().includes(element))
}

function hasLiveOpenDropdown() {
  if (!triggerRef.value?.isConnected) {
    unbindDismissListeners()
    return false
  }
  return isOpen.value
}

function handleDocumentPointerDown(event: PointerEvent) {
  if (!hasLiveOpenDropdown()) return

  const content = document.querySelector(`[data-header-dropdown-content="${dropdownInstanceId}"]`)
  if (eventPathContains(event, triggerRef.value) || eventPathContains(event, content)) return

  dismissDropdown()
}

function handleDocumentKeydown(event: KeyboardEvent) {
  if (!hasLiveOpenDropdown() || event.key !== 'Escape') return
  event.preventDefault()
  dismissDropdown(true)
}

function handleEscapeKeyDown(event: Event) {
  event.preventDefault()
  dismissDropdown(true)
}

function bindDismissListeners() {
  document.addEventListener('pointerdown', handleDocumentPointerDown, true)
  document.addEventListener('keydown', handleDocumentKeydown, true)
}

function unbindDismissListeners() {
  document.removeEventListener('pointerdown', handleDocumentPointerDown, true)
  document.removeEventListener('keydown', handleDocumentKeydown, true)
}

function shouldSearchBackend(query: string, localMatches: DropdownOption[]) {
  return typeof props.backendSearch === 'function'
    && query.length >= props.backendSearchMinChars
    && localMatches.length === 0
}

function scheduleBackendSearch(query: string) {
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
  backendSearchTimer = setTimeout(() => void runBackendSearch(query), Math.max(0, props.backendSearchDebounceMs))
}

async function runBackendSearch(query: string) {
  if (!props.backendSearch) return
  const token = ++backendSearchToken
  backendLoading.value = true
  try {
    const result = await props.backendSearch(query, props.backendSearchLimit)
    if (token !== backendSearchToken) return
    const raw = Array.isArray(result)
      ? result
      : (result && typeof result === 'object' && Array.isArray((result as { models?: unknown[] }).models)
          ? (result as { models: unknown[] }).models
          : [])
    backendOptions.value = normalizeModelOptions(raw) as DropdownOption[]
  } catch {
    if (token === backendSearchToken) backendOptions.value = []
  } finally {
    if (token === backendSearchToken) backendLoading.value = false
  }
}

function optionKey(option: DropdownOption, fallbackIndex: number, prefix = '') {
  const keyPrefix = prefix ? `${prefix}:` : ''
  return `${keyPrefix}${String(option.key ?? option.value ?? fallbackIndex)}`
}

function resolveProvider(option: DropdownOption) {
  if (option.provider) return option.provider
  const rawValue = String(option.value || '')
  return rawValue.includes('/') ? rawValue.split('/')[0].trim() : ''
}

function normalizeProviderKey(provider: string) {
  return provider.trim().toLowerCase() || 'other'
}

onBeforeUnmount(() => {
  if (backendSearchTimer) clearTimeout(backendSearchTimer)
  unbindDismissListeners()
})
</script>

<template>
  <div class="relative" :class="maxWidthClass" :style="containerStyle">
    <ComboboxRoot
      :model-value="modelValue"
      :open="isOpen"
      :disabled="disabled"
      :ignore-filter="true"
      :reset-search-term-on-select="true"
      @update:model-value="handleChange"
      @update:open="handleOpenChange"
    >
      <ComboboxAnchor as-child>
        <div class="relative">
          <ComboboxTrigger as-child>
            <button
              ref="triggerRef"
              type="button"
              class="group inline-flex w-full items-center justify-between gap-2 rounded-md border px-2.5 py-1 text-[13px] font-medium transition-colors outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-focus-ring)] disabled:cursor-not-allowed disabled:opacity-50"
              :style="triggerStyle"
              :aria-label="ariaLabel"
              :disabled="disabled"
            >
              <span class="flex min-w-0 items-center gap-2">
                <span v-if="selectedOption?.icon" class="inline-flex h-4 w-4 shrink-0" data-header-dropdown-icon>
                  <component :is="selectedOption.icon" class="h-4 w-4 text-[var(--color-text-muted)]" aria-hidden="true" />
                </span>
                <span class="truncate" :title="selectedLabel">{{ selectedLabel }}</span>
              </span>
              <ChevronUpDownIcon class="h-3.5 w-3.5 shrink-0 opacity-70 transition-transform group-data-[state=open]:rotate-180" aria-hidden="true" />
            </button>
          </ComboboxTrigger>

          <ComboboxPortal>
            <ComboboxContent
              :class="[dropdownSurfaceClass, 'ui-combobox-content']"
              :style="floatingOptionsStyle"
              position="popper"
              :side-offset="6"
              align="start"
              position-strategy="fixed"
              :collision-padding="8"
              :data-header-dropdown-content="dropdownInstanceId"
              @escape-key-down="handleEscapeKeyDown"
              @pointer-down-outside="dismissDropdown()"
              @focus-outside="dismissDropdown()"
            >
              <div v-if="searchable" :class="dropdownSearchRowClass" :style="dropdownSearchRowStyle">
                <ComboboxInput
                  v-model="searchQuery"
                  :class="dropdownSearchInputClass"
                  :placeholder="searchPlaceholder"
                  :style="dropdownSearchInputStyle"
                  :aria-label="searchPlaceholder"
                />
              </div>
              <div v-if="backendLoading && searchable && searchQuery" class="px-3 pb-1 text-[11px]" :style="dropdownMutedTextStyle">
                Searching...
              </div>

              <ComboboxViewport class="max-h-[240px] overflow-y-auto">
                <template v-if="groupByProvider">
                  <template v-for="group in groupedFilteredOptions" :key="group.key">
                    <div :class="dropdownGroupLabelClass" :style="dropdownMutedTextStyle">{{ group.label }}</div>
                    <ComboboxItem
                      v-for="(option, index) in group.options"
                      :key="optionKey(option, index, group.key)"
                      :value="option.value"
                      :text-value="option.label"
                      :class="[dropdownOptionClass, 'relative flex pl-3 pr-9 data-[highlighted]:bg-[var(--color-panel-muted)] data-[state=checked]:font-semibold']"
                      :title="option.label"
                    >
                      <span class="flex min-w-0 items-center gap-2 pr-2">
                        <span v-if="option.icon" class="inline-flex h-4 w-4 shrink-0" data-header-dropdown-icon>
                          <component :is="option.icon" class="h-4 w-4 text-[var(--color-text-muted)]" aria-hidden="true" />
                        </span>
                        <span class="truncate">{{ option.label }}</span>
                      </span>
                      <ComboboxItemIndicator class="absolute right-2.5 top-1/2 -translate-y-1/2">
                        <CheckIcon class="h-4 w-4 text-[var(--color-text-muted)]" aria-hidden="true" />
                      </ComboboxItemIndicator>
                    </ComboboxItem>
                  </template>
                </template>
                <template v-else>
                  <ComboboxItem
                    v-for="(option, index) in filteredOptions"
                    :key="optionKey(option, index)"
                    :value="option.value"
                    :text-value="option.label"
                    :class="[dropdownOptionClass, 'relative flex pl-3 pr-9 data-[highlighted]:bg-[var(--color-panel-muted)] data-[state=checked]:font-semibold']"
                    :title="option.label"
                  >
                    <span class="flex min-w-0 items-center gap-2 pr-2">
                      <span v-if="option.icon" class="inline-flex h-4 w-4 shrink-0" data-header-dropdown-icon>
                        <component :is="option.icon" class="h-4 w-4 text-[var(--color-text-muted)]" aria-hidden="true" />
                      </span>
                      <span class="truncate">{{ option.label }}</span>
                    </span>
                    <ComboboxItemIndicator class="absolute right-2.5 top-1/2 -translate-y-1/2">
                      <CheckIcon class="h-4 w-4 text-[var(--color-text-muted)]" aria-hidden="true" />
                    </ComboboxItemIndicator>
                  </ComboboxItem>
                </template>
                <ComboboxEmpty :class="dropdownEmptyClass" :style="dropdownMutedTextStyle">
                  {{ noResultsLabel }}
                </ComboboxEmpty>
              </ComboboxViewport>
              <div v-if="$slots.footer" class="sticky bottom-0 border-t border-[var(--color-border)] bg-[var(--color-panel-elevated)] p-1.5">
                <slot name="footer" />
              </div>
            </ComboboxContent>
          </ComboboxPortal>
        </div>
      </ComboboxAnchor>
    </ComboboxRoot>
  </div>
</template>

<style scoped>
.ui-combobox-content[data-state='open'] {
  animation: combobox-in var(--motion-duration-fast) var(--motion-ease-spring);
}

.ui-combobox-content[data-state='closed'] {
  animation: none;
  pointer-events: none;
  visibility: hidden;
}

@keyframes combobox-in {
  from { opacity: 0; transform: translateY(-3px) scale(0.985); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

</style>
