<template>
  <Dialog :open="isOpen" @update:open="handleOpenChange">
    <DialogContent
      class="max-w-lg gap-0 overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-panel-elevated)] p-0 shadow-[var(--shadow-modal)] sm:max-w-lg"
    >
      <DialogHeader class="modal-header pr-12 text-left">
        <DialogTitle class="text-base font-semibold text-[var(--color-text-main)]">
          Keyboard Shortcuts
        </DialogTitle>
        <DialogDescription class="text-sm text-[var(--color-text-muted)]">
          Quick actions available across the workspace.
        </DialogDescription>
      </DialogHeader>

      <div class="max-h-[65vh] overflow-y-auto px-5 py-4">
        <div v-for="category in shortcutCategories" :key="category.name" class="mb-5 last:mb-0">
          <p class="mb-2 text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">
            {{ category.name }}
          </p>
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

      <DialogFooter class="modal-footer m-0 rounded-none border-t border-[var(--color-border)] bg-[var(--color-surface)] p-3">
        <DialogClose as-child>
          <Button variant="outline">Close</Button>
        </DialogClose>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { SHORTCUTS, shortcutLabel, shortcutsByCategory } from '../../utils/keyboardShortcuts'

withDefaults(defineProps<{ isOpen?: boolean }>(), {
  isOpen: false,
})

const emit = defineEmits<{ close: [] }>()
const platform = typeof navigator !== 'undefined' ? navigator.platform : ''
const shortcutCategories = computed(() => {
  const groups = shortcutsByCategory() as Record<string, typeof SHORTCUTS>
  return Object.keys(groups).map((name) => ({ name, items: groups[name] }))
})

function handleOpenChange(open: boolean) {
  if (!open) emit('close')
}
</script>
