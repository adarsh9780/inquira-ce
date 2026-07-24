<template>
  <div class="fixed inset-0 flex items-center justify-center bg-[var(--color-base)]" role="alert">
    <div class="w-full max-w-md px-6 text-center">
      <div class="mb-8 flex justify-center"><img :src="logo" alt="Inquira logo" class="h-16 w-16" /></div>
      <h1 class="text-xl font-semibold tracking-tight text-[var(--color-text-main)]">Startup Failed</h1>
      <p class="mt-3 text-sm text-[var(--color-text-muted)]">The desktop services could not reach a healthy state.</p>
      <div class="mt-8 rounded-lg border border-[var(--color-accent-border)] bg-[var(--color-danger-bg)] px-4 py-3 text-left">
        <p class="text-xs font-medium uppercase tracking-wider text-[var(--color-danger-text)]">Error</p>
        <p class="mt-2 text-sm text-[var(--color-danger-text)]">{{ error }}</p>
      </div>
      <StartupFailureActions
        :message="recoveryMessage"
        @restart="$emit('restart')"
        @open-logs="$emit('openLogs')"
        @copy-diagnostics="$emit('copyDiagnostics')"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import StartupFailureActions from './StartupFailureActions.vue'

defineProps<{ logo: string; error: string; recoveryMessage: string }>()
defineEmits<{ restart: []; openLogs: []; copyDiagnostics: [] }>()
</script>
