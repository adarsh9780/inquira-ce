<template>
  <div class="segmented-control" role="tablist" :aria-label="ariaLabel">
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      role="tab"
      class="segmented-control-item"
      :class="modelValue === option.value ? 'segmented-control-item-active' : ''"
      :aria-selected="modelValue === option.value"
      :title="option.label"
      @click="emit('update:modelValue', option.value)"
    >
      <component :is="option.icon" v-if="option.icon" class="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      <span>{{ option.label }}</span>
      <span
        v-if="(option.count || 0) > 0"
        :data-segment-count="option.value"
        class="inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-[var(--color-panel-muted)] px-1 text-[10px] font-semibold leading-none text-[var(--color-text-muted)]"
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
}>(), {
  options: () => [],
  ariaLabel: 'View',
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()
</script>
