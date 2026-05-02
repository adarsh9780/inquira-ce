<template>
  <div class="flex h-full min-w-0 flex-col gap-3 overflow-hidden rounded-xl border p-3" style="background-color: var(--color-base); border-color: var(--color-border);">
    <div class="min-w-0 rounded-xl border p-3" style="border-color: var(--color-border); background-color: var(--color-surface);">
      <div class="flex items-center justify-between gap-3">
        <p class="text-xs uppercase tracking-wide" style="color: var(--color-text-muted);">Question</p>
        <span
          v-if="isFinalTurn"
          class="rounded-full border px-2 py-0.5 text-[11px] font-semibold"
          style="border-color: var(--color-border); color: var(--color-accent);"
        >
          Final
        </span>
      </div>
      <p class="mt-1 text-sm" style="color: var(--color-text-main);">{{ appStore.activeTurn?.user_text || 'No turn selected.' }}</p>
    </div>

    <div class="min-h-0 flex-1 overflow-auto rounded-xl border p-3" style="border-color: var(--color-border); background-color: var(--color-surface);">
      <p class="text-xs uppercase tracking-wide" style="color: var(--color-text-muted);">Answer</p>
      <p class="mt-1 whitespace-pre-wrap text-sm" style="color: var(--color-text-main);">{{ appStore.activeTurn?.assistant_text || '' }}</p>

      <p class="mt-4 text-xs uppercase tracking-wide" style="color: var(--color-text-muted);">Code</p>
      <pre class="mt-1 overflow-auto rounded-lg p-3 text-xs" style="background-color: var(--color-base); color: var(--color-text-main);">{{ appStore.activeTurnCode || '# No code snapshot' }}</pre>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useAppStore } from '../../stores/appStore'

const appStore = useAppStore()
const isFinalTurn = computed(() => String(appStore.finalTurnId || '') === String(appStore.activeTurnId || ''))
</script>
