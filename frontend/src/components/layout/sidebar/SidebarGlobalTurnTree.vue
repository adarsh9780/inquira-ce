<template>
  <div
    :class="variant === 'page'
      ? 'min-h-0 flex flex-1 flex-col overflow-hidden'
      : 'mt-1 flex min-h-0 flex-col pl-3 pr-1 pb-2'"
  >
    <div class="flex shrink-0 items-center justify-end px-1 pb-2">
      <button
        type="button"
        class="btn-icon"
        aria-label="Open conversation tree rules"
        title="Conversation tree rules"
        @click="rulesDialogOpen = true"
      >
        <ExclamationCircleIcon class="h-5 w-5" />
      </button>
    </div>
    <div v-if="isLoading" :class="variant === 'page' ? 'px-2 py-6 text-sm text-[var(--color-text-muted)]' : 'px-2 py-2 text-[11px] text-[var(--color-text-muted)]'">
      Loading tree...
    </div>
    <TurnTreeGraphView
      v-else
      :conversations="conversations"
      :current-turn-id="appStore.activeTurnId"
      :current-parent-turn-id="appStore.activeTurnRelations?.parent?.id || ''"
      :variant="variant"
      empty-label="No conversation turns yet."
      @select="selectTurn"
      @mark-final="markTurnFinal"
      @delete-turn="deleteTurn"
    />
    <ConversationTreeRulesModal :is-open="rulesDialogOpen" @close="rulesDialogOpen = false" />
    <ConfirmationModal
      :is-open="deleteDialogOpen"
      title="Delete Turn and Replies"
      message="Delete this turn and all replies below it? If this is the root turn, the entire conversation will be deleted."
      confirm-text="Delete"
      cancel-text="Cancel"
      @close="closeDeleteDialog"
      @confirm="confirmDeleteTurn"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ExclamationCircleIcon } from '@heroicons/vue/24/outline'
import { useAppStore } from '../../../stores/appStore'
import { toast } from '../../../composables/useToast'
import { extractApiErrorMessage } from '../../../utils/apiError'
import TurnTreeGraphView from '../../chat/TurnTreeGraphView.vue'
import ConfirmationModal from '../../modals/ConfirmationModal.vue'
import ConversationTreeRulesModal from '../../modals/ConversationTreeRulesModal.vue'

defineProps({
  variant: { type: String, default: 'sidebar' },
})

const appStore = useAppStore()
const isLoading = ref(false)
const rulesDialogOpen = ref(false)
const deleteDialogOpen = ref(false)
const pendingDeletePayload = ref(null)

const conversations = computed(() => {
  const raw = appStore.workspaceTurnTree?.conversations
  return Array.isArray(raw) ? raw : []
})

async function refreshTree() {
  if (!appStore.activeWorkspaceId) return
  isLoading.value = true
  try {
    await appStore.loadWorkspaceTurnTree()
  } catch (error) {
    toast.error('Tree load failed', extractApiErrorMessage(error, 'Unable to load conversation tree.'))
  } finally {
    isLoading.value = false
  }
}

async function selectTurn(payload) {
  const targetConversationId = String(payload?.conversationId || '').trim()
  const targetTurnId = String(payload?.turnId || '').trim()
  if (!targetConversationId || !targetTurnId) return
  try {
    if (targetConversationId !== appStore.activeConversationId) {
      appStore.setActiveConversationId(targetConversationId)
      await appStore.fetchConversationTurns({ reset: true })
    }
    await appStore.loadActiveTurnRelations(targetTurnId)
    appStore.setActiveTab('workspace')
    appStore.setWorkspacePane?.('chat')
  } catch (error) {
    toast.error('Turn load failed', extractApiErrorMessage(error, 'Unable to open this turn.'))
  }
}

async function markTurnFinal(payload) {
  try {
    await appStore.markTurnFinal(payload?.turnId, payload?.conversationId)
    toast.success('Final turn updated', 'This turn is now marked final.')
  } catch (error) {
    toast.error('Final turn failed', extractApiErrorMessage(error, 'Unable to mark final turn.'))
  }
}

function deleteTurn(payload) {
  pendingDeletePayload.value = payload || null
  deleteDialogOpen.value = true
}

function closeDeleteDialog() {
  deleteDialogOpen.value = false
  pendingDeletePayload.value = null
}

async function confirmDeleteTurn() {
  const payload = pendingDeletePayload.value
  closeDeleteDialog()
  try {
    await appStore.deleteTurn(payload?.turnId, payload?.conversationId)
    toast.success('Turn deleted', 'The turn was removed from the tree.')
  } catch (error) {
    toast.error('Delete failed', extractApiErrorMessage(error, 'Unable to delete this turn.'))
  }
}

onMounted(() => {
  void refreshTree()
})

watch(() => appStore.activeWorkspaceId, () => {
  void refreshTree()
})
</script>
