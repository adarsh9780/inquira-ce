<template>
  <div class="relative" :class="maxWidthClass" :style="containerStyle">
    <Listbox :model-value="modelValue" @update:model-value="handleChange">
      <div class="relative">
        <ListboxButton
          class="inline-flex w-full items-center justify-between gap-2 rounded-md border px-2.5 py-1 text-[13px] font-medium transition-colors focus:outline-none"
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
            <ListboxOption
              v-for="(option, index) in options"
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
                class="relative cursor-default select-none py-2 pl-3 pr-9 text-[13px]"
              >
                <span :class="selected ? 'font-semibold' : 'font-normal'" class="block truncate pr-2" :title="option.label">
                  {{ option.label }}
                </span>
                <span v-if="selected" class="absolute right-2.5 top-1/2 -translate-y-1/2">
                  <CheckIcon class="h-4 w-4" style="color: var(--color-text-muted);" />
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
import { computed } from 'vue'
import { Listbox, ListboxButton, ListboxOption, ListboxOptions } from '@headlessui/vue'
import { CheckIcon, ChevronUpDownIcon } from '@heroicons/vue/20/solid'

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
  }
})

const emit = defineEmits(['update:modelValue'])

const selectedOption = computed(() => props.options.find((option) => option.value === props.modelValue) ?? null)
const selectedLabel = computed(() => selectedOption.value?.label || props.placeholder)
const hasSelection = computed(() => !!selectedOption.value)
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
    maxWidth: '45vw'
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

function optionKey(option, fallbackIndex) {
  if (option?.key != null) return String(option.key)
  if (option?.value != null) return String(option.value)
  return String(fallbackIndex)
}
</script>
