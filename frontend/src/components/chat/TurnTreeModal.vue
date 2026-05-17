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

        <div class="min-h-0 flex-1 overflow-y-auto px-5 py-4">
          <div v-if="roots.length === 0" class="rounded-lg border border-dashed border-[var(--color-border)] px-4 py-8 text-center text-sm text-[var(--color-text-muted)]">
            No turns yet.
          </div>
          <div v-else class="space-y-1.5">
            <TurnTreeBranch
              v-for="node in roots"
              :key="node.id"
              :node="node"
              :current-turn-id="currentTurnId"
              :final-turn-id="finalTurnId"
              @select="selectNode"
              @mark-final="markFinalNode"
            />
          </div>
        </div>

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
import { onMounted, onUnmounted } from 'vue'
import TurnTreeBranch from './TurnTreeBranch.vue'

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
  finalTurnId: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['close', 'select', 'mark-final', 'rerun-final'])

function closeModal() {
  emit('close')
}

function selectNode(turnId) {
  emit('select', turnId)
}

function markFinalNode(turnId) {
  emit('mark-final', turnId)
}

function rerunFinalTurn() {
  emit('rerun-final')
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
