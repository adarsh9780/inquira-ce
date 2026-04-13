<template>
  <section>
    <h2 class="mb-4 text-lg font-bold text-[var(--color-text-main)]">LLM &amp; API Keys</h2>

    <div class="space-y-4">
      <div>
        <label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-[var(--color-text-sub)]">Provider</label>
        <div class="relative">
          <select
            v-model="provider"
            class="w-full appearance-none rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base-soft)] px-3 py-2 pr-9 text-sm text-[var(--color-text-main)] outline-none focus:border-[var(--color-accent)] focus:ring-2 focus:ring-[var(--color-accent)]/20"
          >
            <option value="openai">OpenAI</option>
            <option value="openrouter">OpenRouter</option>
            <option value="ollama">Ollama (local)</option>
          </select>
          <svg class="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-text-muted)]" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8">
            <path d="M6 8l4 4 4-4" />
          </svg>
        </div>
      </div>

      <div v-if="provider !== 'ollama'">
        <label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-[var(--color-text-sub)]">API Key</label>
        <div class="relative">
          <input
            v-model="apiKey"
            :type="showKey ? 'text' : 'password'"
            class="w-full rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base-soft)] px-3 py-2 pr-10 text-sm text-[var(--color-text-main)] outline-none focus:border-[var(--color-accent)] focus:ring-2 focus:ring-[var(--color-accent)]/20"
          />
          <button
            type="button"
            class="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-[var(--color-text-muted)] hover:bg-[var(--color-base-muted)] hover:text-[var(--color-text-main)]"
            @click="showKey = !showKey"
            :aria-label="showKey ? 'Hide key' : 'Show key'"
          >
            <svg v-if="!showKey" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6z" />
              <circle cx="12" cy="12" r="2.8" />
            </svg>
            <svg v-else class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <path d="M3 3l18 18" />
              <path d="M10.6 10.6a2 2 0 0 0 2.8 2.8" />
              <path d="M9.8 5.4A11.3 11.3 0 0 1 12 5c6.5 0 10 7 10 7a16.3 16.3 0 0 1-3.1 3.9" />
              <path d="M6.6 6.6C3.5 8.6 2 12 2 12s3.5 7 10 7c1.2 0 2.3-.2 3.2-.5" />
            </svg>
          </button>
        </div>
      </div>

      <div v-else>
        <label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-[var(--color-text-sub)]">Ollama Base URL</label>
        <input
          v-model="ollamaBaseUrl"
          type="text"
          class="w-full rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base-soft)] px-3 py-2 text-sm text-[var(--color-text-main)] outline-none focus:border-[var(--color-accent)] focus:ring-2 focus:ring-[var(--color-accent)]/20"
        />
      </div>

      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-[var(--color-text-sub)]">Main model</label>
          <div class="relative">
            <select
              v-model="mainModel"
              class="w-full appearance-none rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base-soft)] px-3 py-2 pr-9 text-sm text-[var(--color-text-main)] outline-none focus:border-[var(--color-accent)] focus:ring-2 focus:ring-[var(--color-accent)]/20"
            >
              <option value="gpt-5.4">gpt-5.4</option>
              <option value="gpt-5.4-mini">gpt-5.4-mini</option>
              <option value="gpt-5.2">gpt-5.2</option>
            </select>
            <svg class="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-text-muted)]" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8">
              <path d="M6 8l4 4 4-4" />
            </svg>
          </div>
        </div>

        <div>
          <label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-[var(--color-text-sub)]">
            Lite model
            <span class="normal-case tracking-normal font-normal text-xs text-[var(--color-text-muted)]">for quick tasks</span>
          </label>
          <div class="relative">
            <select
              v-model="liteModel"
              class="w-full appearance-none rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-base-soft)] px-3 py-2 pr-9 text-sm text-[var(--color-text-main)] outline-none focus:border-[var(--color-accent)] focus:ring-2 focus:ring-[var(--color-accent)]/20"
            >
              <option value="gpt-5.4-mini">gpt-5.4-mini</option>
              <option value="gpt-5.2">gpt-5.2</option>
              <option value="o4-mini">o4-mini</option>
            </select>
            <svg class="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-text-muted)]" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8">
              <path d="M6 8l4 4 4-4" />
            </svg>
          </div>
        </div>
      </div>

      <div class="rounded-lg border border-[var(--color-accent-border)] bg-[var(--color-accent-soft)] p-3 text-sm text-[var(--color-text-sub)]">
        Main model handles deep analysis and long reasoning. Lite model runs fast summarization and helper actions to keep chats responsive.
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <span class="inline-flex items-center gap-1 rounded-full bg-[var(--color-success-bg)] px-3 py-1 text-xs text-[var(--color-success)]">
          <span class="h-1.5 w-1.5 rounded-full bg-[var(--color-success)]"></span>
          API key set
        </span>
        <span class="inline-flex items-center gap-1 rounded-full bg-[var(--color-success-bg)] px-3 py-1 text-xs text-[var(--color-success)]">
          <span class="h-1.5 w-1.5 rounded-full bg-[var(--color-success)]"></span>
          Ready to analyse
        </span>
      </div>

      <div class="mt-5 flex justify-end gap-2 border-t border-[var(--color-border)] pt-4">
        <button type="button" class="rounded-lg border border-[var(--color-border-strong)] px-4 py-2 text-sm text-[var(--color-text-sub)] transition-all hover:bg-[var(--color-base-soft)] font-medium">
          Cancel
        </button>
        <button type="button" class="rounded-lg bg-[var(--color-accent)] px-4 py-2 text-sm text-white transition-all hover:brightness-90 font-medium">
          Save
        </button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref } from 'vue'

const provider = ref('openai')
const apiKey = ref('sk-••••••••••••••••••••YzBp')
const showKey = ref(false)
const mainModel = ref('gpt-5.4')
const liteModel = ref('gpt-5.4-mini')
const ollamaBaseUrl = ref('http://localhost:11434')
</script>
