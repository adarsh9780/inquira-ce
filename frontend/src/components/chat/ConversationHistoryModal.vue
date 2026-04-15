<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 layer-modal overflow-y-auto"
    role="dialog"
    aria-modal="true"
  >
    <div class="modal-overlay" @click="closeModal"></div>

    <div class="flex min-h-full items-center justify-center p-4">
      <div class="modal-card relative w-full max-w-lg" @click.stop>
        <div class="modal-header flex-col items-start gap-1">
          <h3 class="text-base font-semibold text-[var(--color-text-main)]">Conversation History</h3>
          <p class="text-sm text-[var(--color-text-muted)]">Select a past conversation to continue.</p>
        </div>

        <div class="max-h-80 overflow-y-auto p-3">
          <div v-if="conversations.length === 0" class="rounded-lg border border-dashed border-[var(--color-border)] px-4 py-8 text-center text-sm text-[var(--color-text-muted)]">
            No conversations yet.
          </div>
          <button
            v-for="conv in conversations"
            :key="conv.id"
            type="button"
            class="mb-2 w-full rounded-lg border px-3 py-2 text-left transition-colors"
            :class="conv.id === activeConversationId
              ? 'border-[var(--color-accent-border)] bg-[var(--color-accent-soft)]'
              : 'border-[var(--color-border)] hover:bg-[var(--color-base-soft)]'"
            @click="selectConversation(conv.id)"
          >
            <p class="truncate text-sm font-medium text-[var(--color-text-main)]">{{ conv.title || 'Conversation' }}</p>
            <p class="mt-0.5 text-xs text-[var(--color-text-muted)]">{{ formatTimestamp(conv.updated_at || conv.created_at) }}</p>
          </button>
        </div>

        <div class="modal-footer px-5 py-4">
          <button
            type="button"
            class="btn-secondary px-3 py-2 text-sm"
            @click="closeModal"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { formatTimestamp } from '../../utils/dateUtils'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  conversations: {
    type: Array,
    default: () => []
  },
  activeConversationId: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['close', 'select'])

function closeModal() {
  emit('close')
}

function selectConversation(conversationId) {
  emit('select', conversationId)
}

function handleEscape(event) {
  if (event.key === 'Escape' && props.isOpen) {
    closeModal()
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleEscape)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleEscape)
})
</script>
