<template>
  <div class="absolute inset-0 flex items-center justify-center" style="background-color: var(--color-base);">
    <div class="text-center">
      <slot name="icon" />
      <p class="text-sm" style="color: var(--color-text-muted);">{{ title }}</p>
      <p v-if="subtitle" class="text-xs mt-1" style="color: var(--color-text-muted);">{{ subtitle }}</p>
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
