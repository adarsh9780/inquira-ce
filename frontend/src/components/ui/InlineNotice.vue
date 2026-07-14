<template>
  <div class="inline-notice" role="status">
    <div class="min-w-0">
      <p class="truncate text-xs font-medium text-[var(--color-text-main)]">{{ title }}</p>
      <p v-if="message" class="mt-0.5 truncate text-[11px] text-[var(--color-text-muted)]">{{ message }}</p>
    </div>
    <button v-if="actionLabel" type="button" class="shrink-0 text-xs font-semibold text-[var(--color-accent)]" @click="emit('action')">
      {{ actionLabel }}
    </button>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  message: { type: String, default: '' },
  actionLabel: { type: String, default: '' },
})
const emit = defineEmits(['action'])
</script>

