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
      <span v-if="option.indicator" class="new-content-dot" aria-label="New content" />
    </button>
  </div>
</template>

<script setup>
defineProps({
  modelValue: { type: String, required: true },
  options: { type: Array, default: () => [] },
  ariaLabel: { type: String, default: 'View' },
})
const emit = defineEmits(['update:modelValue'])
</script>
