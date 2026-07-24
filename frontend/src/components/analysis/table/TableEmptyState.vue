<template>
  <div class="absolute inset-0" style="background-color: var(--color-base);">
    <AppEmptyState :title="title" :description="subtitle"><template #icon><slot name="icon" /></template></AppEmptyState>
  </div>
</template>

<script setup lang="ts">
import AppEmptyState from '../../ui/AppEmptyState.vue'
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
