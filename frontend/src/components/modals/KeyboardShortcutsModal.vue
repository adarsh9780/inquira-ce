<script setup lang="ts">
import { computed } from 'vue'
import { Button } from '../ui/button'
import { DialogShell } from '../ui/dialog'
import { SHORTCUTS, shortcutLabel, shortcutsByCategory } from '../../utils/keyboardShortcuts'

withDefaults(defineProps<{ isOpen?: boolean }>(), { isOpen: false })
const emit = defineEmits<{ close: [] }>()

const platform = typeof navigator !== 'undefined' ? navigator.platform : ''
const shortcutCategories = computed(() => {
  const groups = shortcutsByCategory() as Record<string, typeof SHORTCUTS>
  return Object.keys(groups).map((name) => ({ name, items: groups[name] }))
})
</script>

<template>
  <DialogShell
    :open="isOpen"
    title="Keyboard Shortcuts"
    description="Quick actions available across the workspace."
    content-class="max-w-lg"
    @close="emit('close')"
  >
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
    <template #footer>
      <div class="modal-footer px-5 py-4">
        <Button variant="secondary" @click="emit('close')">Close</Button>
      </div>
    </template>
  </DialogShell>
</template>
