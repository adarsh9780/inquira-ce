<template>
  <Transition
    enter-active-class="dialog-fade-enter-active dialog-pop-enter-active"
    enter-from-class="dialog-fade-enter-from dialog-pop-enter-from"
    leave-active-class="dialog-fade-leave-active dialog-pop-leave-active"
    leave-to-class="dialog-fade-leave-to dialog-pop-leave-to"
  >
    <div
      v-if="isOpen"
      class="fixed inset-0 layer-modal overflow-y-auto"
      aria-labelledby="conversation-tree-rules-title"
      role="dialog"
      aria-modal="true"
    >
      <div class="modal-overlay" @click="closeModal"></div>
      <div class="flex min-h-full items-center justify-center p-4 text-center sm:p-0">
        <div class="modal-card relative w-full max-w-lg text-left sm:my-8" @click.stop>
          <div class="modal-header flex items-center justify-between">
            <div class="flex items-center gap-3">
              <ExclamationCircleIcon class="h-5 w-5 shrink-0 text-[var(--color-accent)]" />
              <h3 id="conversation-tree-rules-title" class="text-base font-semibold text-[var(--color-text-main)]">
                Conversation Tree Rules
              </h3>
            </div>
            <button type="button" class="btn-icon" aria-label="Close conversation tree rules" @click="closeModal">
              <XMarkIcon class="h-5 w-5" />
            </button>
          </div>

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

          <div class="modal-footer justify-end">
            <button type="button" class="btn-primary px-4 py-2 text-sm" @click="closeModal">Close</button>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { ExclamationCircleIcon, XMarkIcon } from '@heroicons/vue/24/outline'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['close'])

function closeModal() {
  emit('close')
}

function handleEscape(event) {
  if (event.key === 'Escape' && props.isOpen) closeModal()
}

onMounted(() => document.addEventListener('keydown', handleEscape))
onUnmounted(() => document.removeEventListener('keydown', handleEscape))
</script>
