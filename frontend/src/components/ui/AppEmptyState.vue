<template>
  <div class="app-empty-state">
    <div v-if="$slots.icon" class="app-empty-state-icon"><slot name="icon" /></div>
    <h3 class="app-empty-state-title">{{ title }}</h3>
    <p v-if="description" class="app-empty-state-description">{{ description }}</p>
    <button v-if="actionLabel" type="button" class="btn-secondary mt-4 px-3 py-1.5 text-xs" @click="emit('action')">
      {{ actionLabel }}
    </button>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  description: { type: String, default: '' },
  actionLabel: { type: String, default: '' },
})
const emit = defineEmits(['action'])
</script>

