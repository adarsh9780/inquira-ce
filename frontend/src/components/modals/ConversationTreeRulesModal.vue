<template>
  <Dialog :open="isOpen" @update:open="handleOpenChange">
    <DialogContent
      class="max-w-lg gap-0 overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-panel-elevated)] p-0 shadow-[var(--shadow-modal)] sm:max-w-lg"
    >
      <DialogHeader class="modal-header pr-12 text-left">
        <div class="flex items-center gap-3">
          <ExclamationCircleIcon
            class="h-5 w-5 shrink-0 text-[var(--color-accent)]"
            aria-hidden="true"
          />
          <DialogTitle class="text-base font-semibold text-[var(--color-text-main)]">
            Conversation Tree Rules
          </DialogTitle>
        </div>
        <DialogDescription class="sr-only">
          Rules for navigating and deleting conversation tree nodes.
        </DialogDescription>
      </DialogHeader>

      <div class="space-y-5 px-6 py-5 text-sm text-[var(--color-text-muted)]">
        <section>
          <h4 class="font-semibold text-[var(--color-text-main)]">Using the tree</h4>
          <ul class="mt-2 list-disc space-y-1.5 pl-5">
            <li>Select a node to open that turn.</li>
            <li>Branches show replies created from an earlier turn.</li>
            <li>Nodes cannot be moved or reordered.</li>
            <li>Only successful turns with persisted outputs can be marked final.</li>
          </ul>
        </section>

        <section>
          <h4 class="font-semibold text-[var(--color-text-main)]">Deleting nodes</h4>
          <ul class="mt-2 list-disc space-y-1.5 pl-5">
            <li>Deleting a non-root node removes that turn, all replies below it, and their saved artifacts.</li>
            <li>Deleting a root node removes the entire conversation.</li>
            <li>Deletion cannot be undone.</li>
            <li>If the deleted branch contains the final turn, the deleted node's parent becomes final.</li>
          </ul>
        </section>
      </div>

      <DialogFooter class="modal-footer m-0 rounded-none border-t border-[var(--color-border)] bg-[var(--color-surface)] p-3">
        <DialogClose as-child>
          <Button>Close</Button>
        </DialogClose>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { ExclamationCircleIcon } from '@heroicons/vue/24/outline'
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

withDefaults(defineProps<{ isOpen?: boolean }>(), {
  isOpen: false,
})

const emit = defineEmits<{ close: [] }>()

function handleOpenChange(open: boolean) {
  if (!open) emit('close')
}
</script>
