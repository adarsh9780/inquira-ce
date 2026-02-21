<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-[70] overflow-y-auto"
    role="dialog"
    aria-modal="true"
  >
    <div class="fixed inset-0 bg-gray-500 bg-opacity-70" @click="closeModal"></div>

    <div class="flex min-h-full items-center justify-center p-4">
      <div class="relative w-full max-w-lg rounded-xl bg-white shadow-xl" @click.stop>
        <div class="border-b border-gray-200 px-5 py-4">
          <h3 class="text-base font-semibold text-gray-900">Conversation History</h3>
          <p class="mt-1 text-sm text-gray-500">Select a past conversation to continue.</p>
        </div>

        <div class="max-h-80 overflow-y-auto p-3">
          <div v-if="conversations.length === 0" class="rounded-lg border border-dashed border-gray-300 px-4 py-8 text-center text-sm text-gray-500">
            No conversations yet.
          </div>
          <button
            v-for="conv in conversations"
            :key="conv.id"
            type="button"
            class="mb-2 w-full rounded-lg border px-3 py-2 text-left hover:bg-gray-50"
            :class="conv.id === activeConversationId ? 'border-blue-300 bg-blue-50' : 'border-gray-200'"
            @click="selectConversation(conv.id)"
          >
            <p class="truncate text-sm font-medium text-gray-800">{{ conv.title || 'Conversation' }}</p>
            <p class="mt-0.5 text-xs text-gray-500">{{ formatTimestamp(conv.updated_at || conv.created_at) }}</p>
          </button>
        </div>

        <div class="flex justify-end border-t border-gray-200 px-5 py-4">
          <button
            type="button"
            class="rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
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

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && props.isOpen) {
    closeModal()
  }
})
</script>
