<template>
  <section class="h-full">
    <h2 class="mb-4 text-lg font-bold text-[var(--color-text-main)]">Account</h2>

    <div class="mb-5 flex items-center gap-3 rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base-soft)] p-4">
      <div class="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--color-accent-soft)] text-sm font-medium text-[var(--color-accent)]">
        {{ initials }}
      </div>
      <div class="min-w-0 flex-1">
        <p class="truncate text-sm font-medium text-[var(--color-text-main)]">{{ displayName }}</p>
        <p class="text-xs text-[var(--color-text-muted)]">v{{ version }}</p>
      </div>
      <span class="rounded-full bg-[var(--color-info-bg)] px-3 py-1 text-xs text-[var(--color-info)]">{{ planLabel }}</span>
    </div>

    <div class="grid grid-cols-2 gap-3">
      <label class="space-y-1">
        <span class="block text-xs font-medium uppercase tracking-wider text-[var(--color-text-sub)]">Display name</span>
        <input
          v-model="displayName"
          type="text"
          class="w-full rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base-soft)] px-3 py-2 text-sm text-[var(--color-text-main)] outline-none focus:border-[var(--color-accent)] focus:ring-2 focus:ring-[var(--color-accent)]/20"
        />
      </label>

      <label class="space-y-1">
        <span class="block text-xs font-medium uppercase tracking-wider text-[var(--color-text-sub)]">Theme</span>
        <div class="relative">
          <select
            v-model="theme"
            class="w-full appearance-none rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base-soft)] px-3 py-2 pr-9 text-sm text-[var(--color-text-main)] outline-none focus:border-[var(--color-accent)] focus:ring-2 focus:ring-[var(--color-accent)]/20"
          >
            <option value="system">System default</option>
            <option value="light">Light</option>
            <option value="dark">Dark</option>
          </select>
          <svg class="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-text-muted)]" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8">
            <path d="M6 8l4 4 4-4" />
          </svg>
        </div>
      </label>
    </div>

    <div class="mt-4">
      <label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-[var(--color-text-sub)]">Default LLM provider</label>
      <div class="relative">
        <select
          v-model="defaultProvider"
          class="w-full appearance-none rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base-soft)] px-3 py-2 pr-9 text-sm text-[var(--color-text-main)] outline-none focus:border-[var(--color-accent)] focus:ring-2 focus:ring-[var(--color-accent)]/20"
        >
          <option value="openai">OpenAI</option>
          <option value="openrouter">OpenRouter</option>
          <option value="ollama">Ollama</option>
        </select>
        <svg class="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-text-muted)]" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8">
          <path d="M6 8l4 4 4-4" />
        </svg>
      </div>
    </div>

    <div class="mt-4 overflow-hidden rounded-lg border border-[var(--color-border-strong)]">
      <div class="flex items-center justify-between border-b border-[var(--color-border)] px-4 py-3">
        <div>
          <p class="text-sm font-medium text-[var(--color-text-main)]">Storage</p>
          <p class="text-xs text-[var(--color-text-muted)]">Local workspace data</p>
        </div>
        <p class="text-sm text-[var(--color-text-main)]">{{ storageUsed }}</p>
      </div>
    </div>

    <div class="mt-5 flex items-center justify-between border-t border-[var(--color-border)] pt-4">
      <button type="button" class="text-sm text-[var(--color-danger)]">Clear all conversation history…</button>

      <div class="flex items-center gap-2">
        <button type="button" class="rounded-lg border border-[var(--color-border-strong)] px-4 py-2 text-sm text-[var(--color-text-sub)] transition-all hover:bg-[var(--color-base-soft)] font-medium">
          Cancel
        </button>
        <button type="button" class="rounded-lg bg-[var(--color-accent)] px-4 py-2 text-sm font-medium text-white transition-all hover:brightness-90">
          Save preferences
        </button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'

const displayName = ref('Adarsh Maurya')
const version = ref('1.0.0')
const planLabel = ref('Free')
const theme = ref('system')
const defaultProvider = ref('openrouter')
const storageUsed = ref('2.1 GB')

const initials = computed(() => {
  const parts = String(displayName.value || '').trim().split(/\s+/).filter(Boolean)
  if (!parts.length) return 'U'
  return parts.slice(0, 2).map((part) => part[0].toUpperCase()).join('')
})
</script>
