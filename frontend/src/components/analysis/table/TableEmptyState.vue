<template>
  <div class="absolute inset-0 flex items-center justify-center" style="background-color: var(--color-base);">
    <div class="max-w-sm px-6 text-center">
      <slot name="icon" />
      <p class="text-sm font-medium" style="color: var(--color-text-main);">{{ title }}</p>
      <p v-if="subtitle" class="text-xs mt-1 leading-5" style="color: var(--color-text-muted);">{{ subtitle }}</p>
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    required: true,
  },
  subtitle: {
    type: String,
    default: '',
  },
})
</script>
