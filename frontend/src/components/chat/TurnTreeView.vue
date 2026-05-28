<template>
  <div :class="rootClass">
    <div v-if="isEmpty" class="rounded-lg border border-dashed border-[var(--color-border)] px-4 py-8 text-center text-sm text-[var(--color-text-muted)]">
      {{ emptyLabel }}
    </div>
    <div v-else class="space-y-3">
      <div
        v-for="conversation in normalizedConversations"
        :key="conversation.id"
        class="space-y-1.5"
      >
        <button
          v-if="showConversationHeaders"
          type="button"
          class="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-[13px] font-medium text-[var(--color-text-main)] transition-colors hover:bg-[var(--color-text-main)]/5"
          :title="conversation.title || 'Untitled'"
          @click="toggleConversation(conversation.id)"
        >
          <ChevronRightIcon
            class="h-3 w-3 shrink-0 transition-transform"
            :class="isExpanded(conversation.id) ? 'rotate-90' : ''"
          />
          <span class="truncate">{{ conversation.title || 'Untitled' }}</span>
        </button>

        <div
          v-show="!showConversationHeaders || isExpanded(conversation.id)"
          :class="showConversationHeaders ? 'ml-4 border-l border-[var(--color-border)] pl-3' : ''"
        >
          <div v-if="conversation.roots.length === 0" class="px-2 py-3 text-sm text-[var(--color-text-muted)]">
            No turns yet.
          </div>
          <div v-else class="space-y-1.5">
            <TurnTreeBranch
              v-for="node in conversation.roots"
              :key="node.id"
              :node="node"
              :current-turn-id="currentTurnId"
              :current-parent-turn-id="currentParentTurnId"
              :final-turn-id="conversation.finalTurnId"
              @select="selectNode(conversation.id, $event)"
              @mark-final="markFinalNode(conversation.id, $event)"
              @open-context-menu="openContextMenu(conversation.id, $event)"
            />
          </div>
        </div>
      </div>
    </div>

    <div
      v-if="contextMenu.open"
      class="fixed z-[85] w-36 rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-elevated)] py-1 shadow-lg"
      :style="{ left: `${contextMenu.x}px`, top: `${contextMenu.y}px` }"
      data-turn-tree-context-menu
    >
      <button
        type="button"
        class="w-full px-3 py-1.5 text-left text-[12px] font-medium text-[var(--color-text-main)] transition-colors hover:bg-[var(--color-panel-muted)]"
        @click="handleContextAction('open')"
      >
        Open
      </button>
      <button
        type="button"
        class="w-full px-3 py-1.5 text-left text-[12px] font-medium text-[var(--color-text-main)] transition-colors hover:bg-[var(--color-panel-muted)]"
        @click="handleContextAction('mark-final')"
      >
        Mark Final
      </button>
      <button
        type="button"
        class="w-full px-3 py-1.5 text-left text-[12px] font-medium text-[var(--color-text-main)] transition-colors hover:bg-[var(--color-panel-muted)]"
        @click="handleContextAction('view-details')"
      >
        View Details
      </button>
      <button
        type="button"
        class="w-full px-3 py-1.5 text-left text-[12px] font-medium transition-colors"
        :class="canDeleteSelected ? 'text-[var(--color-danger)] hover:bg-[var(--color-danger-bg)]' : 'cursor-not-allowed text-[var(--color-text-muted)] opacity-60'"
        :title="selectedDeleteBlockReason || 'Delete leaf turn'"
        :disabled="!canDeleteSelected"
        @click="handleContextAction('delete')"
      >
        Delete
      </button>
    </div>

    <div
      v-if="detailModalOpen"
      class="fixed inset-0 z-[86] flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
    >
      <div class="absolute inset-0 bg-black/25" @click="closeDetailModal"></div>
      <div class="modal-card relative flex w-full max-w-2xl flex-col overflow-hidden" @click.stop>
        <div class="modal-header flex-col items-start gap-1">
          <h3 class="text-base font-semibold text-[var(--color-text-main)]">Turn Details</h3>
          <p class="text-sm text-[var(--color-text-muted)]">Inspect the stored content and artifact summary for this turn.</p>
        </div>
        <div class="max-h-[65vh] overflow-y-auto px-5 py-4 space-y-4">
          <div class="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p class="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">Turn ID</p>
              <p class="mt-1 break-all text-[var(--color-text-main)]">{{ detailTurn?.id || '-' }}</p>
            </div>
            <div>
              <p class="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">Created</p>
              <p class="mt-1 text-[var(--color-text-main)]">{{ formatTimestamp(detailTurn?.created_at) }}</p>
            </div>
          </div>

          <div>
            <p class="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">Question</p>
            <p class="mt-1 whitespace-pre-wrap text-sm text-[var(--color-text-main)]">{{ detailTurn?.user_text || '-' }}</p>
          </div>

          <div>
            <p class="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">Response</p>
            <p class="mt-1 whitespace-pre-wrap text-sm text-[var(--color-text-main)]">{{ detailTurn?.assistant_text || '-' }}</p>
          </div>

          <div>
            <p class="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">Artifacts</p>
            <div v-if="detailArtifacts.length === 0" class="mt-1 text-sm text-[var(--color-text-muted)]">No stored artifacts on this turn.</div>
            <div v-else class="mt-2 space-y-2">
              <div
                v-for="artifact in detailArtifacts"
                :key="artifact.key"
                class="rounded-md border border-[var(--color-border)] px-3 py-2 text-sm"
                style="background-color: color-mix(in srgb, var(--color-surface) 62%, transparent);"
              >
                <div class="flex items-center justify-between gap-3">
                  <p class="font-medium text-[var(--color-text-main)]">{{ artifact.label }}</p>
                  <span class="text-[11px] uppercase tracking-[0.08em] text-[var(--color-text-muted)]">{{ artifact.kind }}</span>
                </div>
                <p v-if="artifact.meta" class="mt-1 text-[12px] text-[var(--color-text-muted)]">{{ artifact.meta }}</p>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer px-5 py-4">
          <button
            type="button"
            class="btn-secondary px-3 py-2 text-sm"
            @click="closeDetailModal"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { ChevronRightIcon } from '@heroicons/vue/24/outline'
import { apiService } from '../../services/apiService'
import { formatTimestamp } from '../../utils/dateUtils'
import TurnTreeBranch from './TurnTreeBranch.vue'

const props = defineProps({
  conversations: {
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
  showConversationHeaders: {
    type: Boolean,
    default: false
  },
  emptyLabel: {
    type: String,
    default: 'No turns yet.'
  },
  variant: {
    type: String,
    default: 'modal'
  }
})

const emit = defineEmits(['select', 'mark-final', 'delete-turn'])
const contextMenu = ref({
  open: false,
  conversationId: '',
  turnId: '',
  x: 0,
  y: 0,
})
const detailModalOpen = ref(false)
const detailTurn = ref(null)
const expandedConversationIds = ref(new Set())

const rootClass = computed(() => (
  props.variant === 'page'
    ? 'min-h-0 flex-1 overflow-y-auto px-1 py-3'
    : 'min-h-0 flex-1 overflow-y-auto px-5 py-4'
))

const normalizedConversations = computed(() => (
  (Array.isArray(props.conversations) ? props.conversations : [])
    .map((conversation) => ({
      id: String(conversation?.id || '').trim(),
      title: String(conversation?.title || '').trim(),
      finalTurnId: String(conversation?.final_turn_id || conversation?.finalTurnId || '').trim(),
      roots: Array.isArray(conversation?.roots) ? conversation.roots : [],
    }))
    .filter((conversation) => conversation.id)
))
const isEmpty = computed(() => (
  normalizedConversations.value.length === 0
  || normalizedConversations.value.every((conversation) => conversation.roots.length === 0)
))

const detailArtifacts = computed(() => {
  const events = Array.isArray(detailTurn.value?.tool_events) ? detailTurn.value.tool_events : []
  return events
    .filter((event) => event && event.type === 'artifact' && event.data)
    .map((event, index) => {
      const artifact = event.data || {}
      const kind = String(artifact.kind || 'artifact')
      const label = String(artifact.display_name || artifact.logical_name || artifact.artifact_id || `artifact_${index + 1}`)
      const columns = Array.isArray(artifact.schema) ? artifact.schema.length : 0
      const rowCount = Number.isFinite(Number(artifact.row_count)) ? Number(artifact.row_count) : null
      const metaParts = []
      if (rowCount !== null) metaParts.push(`${rowCount} rows`)
      if (columns > 0) metaParts.push(`${columns} columns`)
      return {
        key: `${label}-${index}`,
        label,
        kind,
        meta: metaParts.join(' · '),
      }
    })
})

const selectedContext = computed(() => findNodeContext(contextMenu.value.conversationId, contextMenu.value.turnId))
const selectedNode = computed(() => selectedContext.value?.node || null)
const selectedConversation = computed(() => selectedContext.value?.conversation || null)
const selectedDeleteBlockReason = computed(() => {
  const node = selectedNode.value
  if (!node) return 'Turn not found'
  if (!String(node.parent_turn_id || '').trim()) return 'Root turns cannot be deleted'
  if (String(selectedConversation.value?.finalTurnId || '').trim() === String(node.id || '').trim()) return 'Final turn cannot be deleted'
  if (Array.isArray(node.children) && node.children.length > 0) return 'Turns with child turns cannot be deleted'
  if (String(props.currentTurnId || '').trim() === String(node.id || '').trim()) return 'Open another turn before deleting the active turn'
  return ''
})
const canDeleteSelected = computed(() => !selectedDeleteBlockReason.value)

function findNodeContext(conversationId, turnId) {
  const targetConversationId = String(conversationId || '').trim()
  const targetTurnId = String(turnId || '').trim()
  if (!targetConversationId || !targetTurnId) return null
  const conversation = normalizedConversations.value.find((item) => item.id === targetConversationId)
  if (!conversation) return null
  const nodeContext = findNodeInSiblings(conversation.roots, targetTurnId)
  return nodeContext ? { conversation, ...nodeContext } : null
}

function findNodeInSiblings(nodes, turnId, parent = null) {
  const siblings = Array.isArray(nodes) ? nodes : []
  for (const node of siblings) {
    if (String(node?.id || '').trim() === turnId) {
      return { node, parent, siblings }
    }
    const childContext = findNodeInSiblings(node?.children || [], turnId, node)
    if (childContext) return childContext
  }
  return null
}

function isExpanded(conversationId) {
  return expandedConversationIds.value.has(String(conversationId || '').trim())
}

function toggleConversation(conversationId, forceOpen = false) {
  const id = String(conversationId || '').trim()
  if (!id) return
  const next = new Set(expandedConversationIds.value)
  if (forceOpen || !next.has(id)) next.add(id)
  else next.delete(id)
  expandedConversationIds.value = next
}

function selectNode(conversationId, turnId) {
  emit('select', {
    conversationId: String(conversationId || '').trim(),
    turnId: String(turnId || '').trim(),
  })
}

function markFinalNode(conversationId, turnId) {
  emit('mark-final', {
    conversationId: String(conversationId || '').trim(),
    turnId: String(turnId || '').trim(),
  })
}

function openContextMenu(conversationId, payload) {
  const turnId = String(payload?.turnId || '').trim()
  const targetConversationId = String(conversationId || '').trim()
  if (!targetConversationId || !turnId) return
  contextMenu.value = {
    open: true,
    conversationId: targetConversationId,
    turnId,
    x: Number(payload?.x || 0),
    y: Number(payload?.y || 0),
  }
}

function closeContextMenu() {
  contextMenu.value = {
    open: false,
    conversationId: '',
    turnId: '',
    x: 0,
    y: 0,
  }
}

async function handleContextAction(action) {
  const conversationId = String(contextMenu.value.conversationId || '').trim()
  const turnId = String(contextMenu.value.turnId || '').trim()
  closeContextMenu()
  if (!conversationId || !turnId) return
  if (action === 'open') {
    selectNode(conversationId, turnId)
    return
  }
  if (action === 'mark-final') {
    markFinalNode(conversationId, turnId)
    return
  }
  if (action === 'view-details') {
    await openDetailModal(conversationId, turnId)
    return
  }
  if (action === 'delete') {
    emit('delete-turn', { conversationId, turnId })
    return
  }
}

async function openDetailModal(conversationId, turnId) {
  detailTurn.value = await apiService.v1GetTurn(conversationId, turnId)
  detailModalOpen.value = true
}

function closeDetailModal() {
  detailModalOpen.value = false
  detailTurn.value = null
}

function handleEscape(event) {
  if (event.key === 'Escape' && detailModalOpen.value) {
    event.stopImmediatePropagation()
    closeDetailModal()
  }
}

function handleGlobalPointerDown(event) {
  const target = event?.target
  if (!(target instanceof Element)) return
  if (target.closest('[data-turn-tree-context-menu]')) return
  closeContextMenu()
}

onMounted(() => {
  document.addEventListener('keydown', handleEscape)
  document.addEventListener('pointerdown', handleGlobalPointerDown)
  if (props.showConversationHeaders) {
    for (const conversation of normalizedConversations.value) {
      if (conversation.roots.length > 0) toggleConversation(conversation.id, true)
    }
  }
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleEscape)
  document.removeEventListener('pointerdown', handleGlobalPointerDown)
})

watch(() => normalizedConversations.value.map((conversation) => conversation.id).join('|'), () => {
  if (!props.showConversationHeaders) return
  const next = new Set(expandedConversationIds.value)
  for (const conversation of normalizedConversations.value) {
    if (conversation.roots.length > 0) next.add(conversation.id)
  }
  expandedConversationIds.value = next
})
</script>
