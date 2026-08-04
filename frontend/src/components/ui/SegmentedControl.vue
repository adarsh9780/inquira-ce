<template>
  <div class="segmented-control" :data-icon-only="iconOnly || undefined" role="tablist" :aria-label="ariaLabel">
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      role="tab"
      class="segmented-control-item"
      :class="modelValue === option.value ? 'segmented-control-item-active' : ''"
      :aria-selected="modelValue === option.value"
      :aria-label="iconOnly && (option.count || 0) > 0 ? `${option.label}, ${option.count}` : option.label"
      :title="option.label"
      @click="emit('update:modelValue', option.value)"
    >
      <component :is="option.icon" v-if="option.icon" class="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      <span :class="iconOnly ? 'sr-only' : ''">{{ option.label }}</span>
      <span
        v-if="!iconOnly && (option.count || 0) > 0"
        :data-segment-count="option.value"
        class="inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-[var(--color-panel-muted)] px-1 text-[10px] font-semibold leading-none text-[var(--color-text-muted)]"
      >
        {{ option.count }}
      </span>
      <span
        v-else-if="iconOnly && (option.count || 0) > 0"
        class="absolute -right-0.5 -top-0.5 inline-flex h-3.5 min-w-3.5 items-center justify-center rounded-full bg-[var(--color-panel-elevated)] px-0.5 text-[0.5625rem] font-semibold leading-none text-[var(--color-text-muted)] shadow-sm"
        aria-hidden="true"
      >
        {{ option.count }}
      </span>
      <span v-if="option.indicator" class="new-content-dot" aria-label="New content" />
    </button>
  </div>
</template>

<script setup lang="ts">
import type { Component } from 'vue'

interface SegmentedOption {
  value: string
  label: string
  icon?: Component
  count?: number
  indicator?: boolean
}

withDefaults(defineProps<{
  modelValue: string
  options?: SegmentedOption[]
  ariaLabel?: string
  iconOnly?: boolean
}>(), {
  options: () => [],
  ariaLabel: 'View',
  iconOnly: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()
</script>
