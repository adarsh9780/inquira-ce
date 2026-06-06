<template>
  <div>
    <div class="mt-6 flex flex-wrap justify-center gap-3" role="group" aria-label="Startup recovery actions">
      <button class="app-button app-button-primary" type="button" @click="$emit('restart')">
        Restart app
      </button>
      <button class="app-button app-button-secondary" type="button" @click="$emit('open-logs')">
        Open logs
      </button>
      <button class="app-button app-button-secondary" type="button" @click="$emit('copy-diagnostics')">
        Copy diagnostics
      </button>
    </div>
    <p v-if="message" class="mt-3 text-xs text-[var(--color-text-muted)]" aria-live="polite">
      {{ message }}
    </p>
  </div>
</template>

<script setup>
defineProps({
  message: {
    type: String,
    default: '',
  },
})

defineEmits(['restart', 'open-logs', 'copy-diagnostics'])
</script>
