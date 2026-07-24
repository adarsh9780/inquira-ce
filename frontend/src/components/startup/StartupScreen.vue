<template>
  <div class="fixed inset-0 flex items-center justify-center bg-[var(--color-base)]" role="status" aria-live="polite">
    <div class="w-full max-w-md px-6 text-center">
      <div class="mb-8 flex justify-center"><img :src="logo" alt="Inquira logo" class="h-16 w-16" /></div>
      <h1 class="text-2xl font-semibold tracking-tight text-[var(--color-text-main)]">{{ title }}</h1>
      <p class="mt-3 text-sm text-[var(--color-text-muted)]">{{ message }}</p>
      <div class="mt-10">
        <div class="h-px w-full bg-[var(--color-border)]">
          <div class="h-full bg-[var(--color-text-main)] transition-all duration-500 ease-out" :style="{ width: `${progress}%` }"></div>
        </div>
        <div class="mt-4 flex items-center justify-center gap-2">
          <div class="h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--color-text-muted)]"></div>
          <span class="text-xs uppercase tracking-wider text-[var(--color-text-muted)]">Starting</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ logo: string; title: string; message: string; progress: number }>()
</script>
