<template>
  <div v-if="isOpen" class="fixed inset-0 z-[90] flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="keyboard-shortcuts-title">
    <div class="modal-overlay" @click="$emit('close')"></div>
    <div class="modal-card relative flex w-full max-w-lg flex-col overflow-hidden" @click.stop>
      <div class="modal-header">
        <div class="min-w-0">
          <h3 id="keyboard-shortcuts-title" class="text-base font-semibold text-[var(--color-text-main)]">Keyboard Shortcuts</h3>
          <p class="mt-1 text-sm text-[var(--color-text-muted)]">Quick actions available across the workspace.</p>
        </div>
      </div>
      <div class="max-h-[65vh] overflow-y-auto px-5 py-4">
        <div v-for="category in shortcutCategories" :key="category.name" class="mb-5 last:mb-0">
          <p class="mb-2 text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">{{ category.name }}</p>
          <div class="divide-y divide-[var(--color-border)] rounded-md border border-[var(--color-border)]">
            <div v-for="shortcut in category.items" :key="shortcut.id" class="flex items-center justify-between gap-4 px-3 py-2">
              <span class="text-sm text-[var(--color-text-main)]">{{ shortcut.label }}</span>
              <kbd class="shrink-0 rounded border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1 font-mono text-[11px] text-[var(--color-text-muted)]">
                {{ shortcutLabel(shortcut, platform) }}
              </kbd>
            </div>
          </div>
        </div>
      </div>
      <div class="modal-footer px-5 py-4">
        <button type="button" class="btn-secondary px-3 py-2 text-sm" @click="$emit('close')">Close</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { SHORTCUTS, shortcutLabel, shortcutsByCategory } from '../../utils/keyboardShortcuts'

defineProps({
  isOpen: { type: Boolean, default: false },
})
defineEmits(['close'])

const platform = typeof navigator !== 'undefined' ? navigator.platform : ''
const shortcutCategories = computed(() => {
  const groups = shortcutsByCategory(SHORTCUTS)
  return Object.keys(groups).map((name) => ({ name, items: groups[name] }))
})
</script>
