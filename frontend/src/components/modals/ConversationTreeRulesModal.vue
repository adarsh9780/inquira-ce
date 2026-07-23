<script setup lang="ts">
import { ExclamationCircleIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import { Button } from '../ui/button'
import { DialogShell } from '../ui/dialog'

withDefaults(defineProps<{ isOpen?: boolean }>(), { isOpen: false })
const emit = defineEmits<{ close: [] }>()
</script>

<template>
  <DialogShell
    :open="isOpen"
    title="Conversation Tree Rules"
    content-class="max-w-lg"
    @close="emit('close')"
  >
    <template #icon>
      <ExclamationCircleIcon class="h-5 w-5 shrink-0 text-[var(--color-accent)]" aria-hidden="true" />
    </template>
    <template #header-actions>
      <Button variant="ghost" size="icon" aria-label="Close conversation tree rules" @click="emit('close')">
        <XMarkIcon class="h-5 w-5" aria-hidden="true" />
      </Button>
    </template>

    <div class="space-y-5 overflow-y-auto px-6 py-5 text-sm text-[var(--color-text-muted)]">
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

    <template #footer>
      <div class="modal-footer justify-end">
        <Button variant="primary" size="lg" @click="emit('close')">Close</Button>
      </div>
    </template>
  </DialogShell>
</template>
