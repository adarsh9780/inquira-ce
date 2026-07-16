<template>
  <section class="scrollbar-hidden h-full overflow-y-auto">
    <div class="mb-5 flex items-center gap-3 rounded-lg border border-[var(--color-border)] bg-[var(--color-base-soft)] p-4">
      <div class="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--color-accent-soft)] text-sm font-medium text-[var(--color-accent)]">
        {{ initials }}
      </div>
      <div class="min-w-0 flex-1">
        <p class="truncate text-sm font-medium text-[var(--color-text-main)]">{{ displayName }}</p>
        <p v-if="displayEmail" class="truncate text-xs text-[var(--color-text-muted)]">{{ displayEmail }}</p>
        <p class="mt-1 text-xs text-[var(--color-text-muted)]">
          Local workspace mode active.
        </p>
      </div>
    </div>

    <div class="rounded-lg border border-[var(--color-border)] bg-[var(--color-base)] px-3 py-2">
      <p class="text-xs text-[var(--color-text-main)]">Inquira CE stores your workspace locally.</p>
      <p class="mt-1 text-xs text-[var(--color-text-muted)]">
        Account sign-in and cloud sync are not included in this open-source build.
      </p>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { useAuthStore } from '../../../stores/authStore'

const authStore = useAuthStore()

const displayName = computed(() => String(authStore.username || 'Local User').trim() || 'Local User')
const displayEmail = computed(() => String(authStore.user?.email || '').trim())

const initials = computed(() => {
  const parts = String(displayName.value || '').trim().split(/\s+/).filter(Boolean)
  if (!parts.length) return 'U'
  return parts.slice(0, 2).map((part) => part[0].toUpperCase()).join('')
})
</script>
