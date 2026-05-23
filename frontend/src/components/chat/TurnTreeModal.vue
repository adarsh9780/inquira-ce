<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 layer-modal overflow-y-auto"
    role="dialog"
    aria-modal="true"
  >
    <div class="modal-overlay" @click="closeModal"></div>

    <div class="flex min-h-full items-center justify-center p-4">
      <div class="modal-card relative flex h-[78vh] w-full max-w-4xl flex-col overflow-hidden" @click.stop>
        <div class="modal-header flex-col items-start gap-1">
          <h3 class="text-base font-semibold text-[var(--color-text-main)]">Conversation Tree</h3>
          <p class="text-sm text-[var(--color-text-muted)]">Select any turn to restore its chat, artifacts, and workspace state.</p>
        </div>

        <TurnTreeView
          :conversations="treeConversations"
          :current-turn-id="currentTurnId"
          :current-parent-turn-id="currentParentTurnId"
          empty-label="No turns yet."
          @select="selectNode"
          @mark-final="markFinalNode"
          @delete-turn="deleteTurn"
          @move-turn="moveTurn"
          @reorder-turns="reorderTurns"
        />

        <div class="modal-footer px-5 py-4">
          <button
            type="button"
            class="btn-secondary px-3 py-2 text-sm"
            :disabled="!finalTurnId"
            @click="rerunFinalTurn"
          >
            Rerun Final
          </button>
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
import { computed, onMounted, onUnmounted } from 'vue'
import TurnTreeView from './TurnTreeView.vue'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  roots: {
    type: Array,
    default: () => []
  },
  currentTurnId: {
    type: String,
    default: ''
  },
  currentParentTurnId: {
    type: String,
    default: ''
  },
  finalTurnId: {
    type: String,
    default: ''
  },
  conversationId: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['close', 'select', 'mark-final', 'rerun-final', 'delete-turn', 'move-turn', 'reorder-turns'])

const treeConversations = computed(() => [{
  id: String(props.conversationId || '').trim(),
  title: 'Conversation',
  final_turn_id: String(props.finalTurnId || '').trim(),
  roots: Array.isArray(props.roots) ? props.roots : [],
}])

function closeModal() {
  emit('close')
}

function selectNode(payload) {
  emit('select', payload?.turnId)
}

function markFinalNode(payload) {
  emit('mark-final', payload?.turnId)
}

function rerunFinalTurn() {
  emit('rerun-final')
}

function deleteTurn(payload) {
  emit('delete-turn', payload?.turnId)
}

function moveTurn(payload) {
  emit('move-turn', {
    turnId: payload?.turnId,
    parentTurnId: payload?.parentTurnId,
  })
}

function reorderTurns(payload) {
  emit('reorder-turns', {
    parentTurnId: payload?.parentTurnId || null,
    turnIds: payload?.turnIds || [],
  })
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
