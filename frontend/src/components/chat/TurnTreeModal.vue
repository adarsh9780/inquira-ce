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
              :current-parent-turn-id="currentParentTurnId"
              :final-turn-id="finalTurnId"
              @select="selectNode"
              @mark-final="markFinalNode"
              @open-context-menu="openContextMenu"
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
              <p class="mt-1 break-all text-[var(--color-text-main)]">{{ detailTurn?.id || '—' }}</p>
            </div>
            <div>
              <p class="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">Created</p>
              <p class="mt-1 text-[var(--color-text-main)]">{{ formatTimestamp(detailTurn?.created_at) }}</p>
            </div>
          </div>

          <div>
            <p class="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">Question</p>
            <p class="mt-1 whitespace-pre-wrap text-sm text-[var(--color-text-main)]">{{ detailTurn?.user_text || '—' }}</p>
          </div>

          <div>
            <p class="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">Response</p>
            <p class="mt-1 whitespace-pre-wrap text-sm text-[var(--color-text-main)]">{{ detailTurn?.assistant_text || '—' }}</p>
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
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { apiService } from '../../services/apiService'
import { formatTimestamp } from '../../utils/dateUtils'
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

const emit = defineEmits(['close', 'select', 'mark-final', 'rerun-final'])
const contextMenu = ref({
  open: false,
  turnId: '',
  x: 0,
  y: 0,
})
const detailModalOpen = ref(false)
const detailTurn = ref(null)

const detailArtifacts = computed(() => {
  const events = Array.isArray(detailTurn.value?.tool_events) ? detailTurn.value.tool_events : []
  return events
    .filter((event) => event && event.type === 'artifact' && event.data)
    .map((event, index) => {
      const artifact = event.data || {}
      const kind = String(artifact.kind || 'artifact')
      const label = String(artifact.logical_name || artifact.artifact_id || `artifact_${index + 1}`)
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

function closeModal() {
  closeContextMenu()
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

function openContextMenu(payload) {
  const turnId = String(payload?.turnId || '').trim()
  if (!turnId) return
  contextMenu.value = {
    open: true,
    turnId,
    x: Number(payload?.x || 0),
    y: Number(payload?.y || 0),
  }
}

function closeContextMenu() {
  contextMenu.value = {
    open: false,
    turnId: '',
    x: 0,
    y: 0,
  }
}

async function handleContextAction(action) {
  const turnId = String(contextMenu.value.turnId || '').trim()
  closeContextMenu()
  if (!turnId) return
  if (action === 'open') {
    selectNode(turnId)
    return
  }
  if (action === 'mark-final') {
    markFinalNode(turnId)
    return
  }
  if (action === 'view-details') {
    await openDetailModal(turnId)
  }
}

async function openDetailModal(turnId) {
  const conversationId = String(props.conversationId || '').trim()
  if (!conversationId) return
  detailTurn.value = await apiService.v1GetTurn(conversationId, turnId)
  detailModalOpen.value = true
}

function closeDetailModal() {
  detailModalOpen.value = false
  detailTurn.value = null
}

function handleEscape(event) {
  if (event.key === 'Escape' && detailModalOpen.value) {
    closeDetailModal()
    return
  }
  if (event.key === 'Escape' && props.isOpen) {
    closeModal()
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
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleEscape)
  document.removeEventListener('pointerdown', handleGlobalPointerDown)
})
</script>
