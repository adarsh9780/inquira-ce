<template>
  <Teleport to="body">
    <div
      data-testid="startup-overlay"
      :data-active="active ? 'true' : 'false'"
      :aria-hidden="active ? 'false' : 'true'"
      role="status"
      aria-live="polite"
      class="layer-blocking fixed inset-0 flex items-center justify-center bg-[var(--color-base)] transition-opacity duration-300"
      :class="active ? 'pointer-events-auto opacity-100' : 'pointer-events-none opacity-0'"
    >
      <div class="w-full max-w-md px-6 text-center">
        <div class="mb-6 flex justify-center"><img :src="logo" alt="Inquira logo" class="h-16 w-16" /></div>
        <p class="text-xs font-medium uppercase tracking-widest text-[var(--color-text-muted)]">{{ pill }}</p>
        <h1 class="mt-4 text-2xl font-semibold tracking-tight text-[var(--color-text-main)]">{{ title }}</h1>
        <p class="mt-3 text-sm text-[var(--color-text-muted)]">{{ message }}</p>
        <div class="mt-8 flex items-center justify-center gap-3">
          <div class="relative h-8 w-8 shrink-0" aria-hidden="true">
            <div class="absolute inset-0 rounded-full border-2 border-[var(--color-border)]"></div>
            <div class="absolute inset-0 animate-spin rounded-full border-2 border-b-transparent border-l-transparent border-r-transparent border-t-[var(--color-text-main)]"></div>
          </div>
          <p class="text-xs text-[var(--color-text-muted)]">{{ elapsed }}</p>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
defineProps<{ active: boolean; logo: string; pill: string; title: string; message: string; elapsed: string }>()
</script>
