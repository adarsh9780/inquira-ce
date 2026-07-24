<template>
  <div
    v-show="!failure && !ready"
    class="fixed inset-0 flex items-center justify-center bg-[var(--color-base)]"
    role="status"
    aria-live="polite"
  >
    <div class="w-full max-w-md px-6 text-center">
      <div class="mb-8 flex justify-center">
        <img :src="logo" alt="Inquira logo" class="h-16 w-16" />
      </div>
      <h1 class="text-2xl font-semibold tracking-tight text-[var(--color-text-main)]">{{ title }}</h1>
      <p class="mt-3 text-sm text-[var(--color-text-muted)]">{{ message }}</p>
      <div class="mt-10">
        <div class="h-px w-full bg-[var(--color-border)]">
          <div
            class="h-full bg-[var(--color-text-main)] transition-all duration-500 ease-out"
            :style="{ width: `${progressPercent}%` }"
          ></div>
        </div>
        <div class="mt-4 flex items-center justify-center gap-2">
          <div class="h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--color-text-muted)]"></div>
          <span class="text-xs uppercase tracking-wider text-[var(--color-text-muted)]">Starting</span>
        </div>
      </div>
    </div>
  </div>

  <div
    v-show="failure"
    class="fixed inset-0 flex items-center justify-center bg-[var(--color-base)]"
    role="alert"
  >
    <div class="w-full max-w-md px-6 text-center">
      <div class="mb-8 flex justify-center">
        <img :src="logo" alt="Inquira logo" class="h-16 w-16" />
      </div>
      <h1 class="text-xl font-semibold tracking-tight text-[var(--color-text-main)]">Startup Failed</h1>
      <p class="mt-3 text-sm text-[var(--color-text-muted)]">The desktop services could not reach a healthy state.</p>
      <div class="mt-8 rounded-lg border border-[var(--color-accent-border)] bg-[var(--color-danger-bg)] px-4 py-3 text-left">
        <p class="text-xs font-medium uppercase tracking-wider text-[var(--color-danger-text)]">Error</p>
        <p class="mt-2 text-sm text-[var(--color-danger-text)]">{{ failure }}</p>
      </div>
      <StartupFailureActions
        :message="recoveryMessage"
        @restart="$emit('restart')"
        @open-logs="$emit('open-logs')"
        @copy-diagnostics="$emit('copy-diagnostics')"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import StartupFailureActions from './StartupFailureActions.vue'

defineProps<{
  ready: boolean
  failure: string
  title: string
  message: string
  progressPercent: number
  recoveryMessage: string
  logo: string
}>()

defineEmits<{
  restart: []
  'open-logs': []
  'copy-diagnostics': []
}>()
</script>
