<template>
  <FloatingActionMenu
    :is-open="contextMenu.open"
    :position="{ x: contextMenu.x, y: contextMenu.y }"
    :items="actions"
    marker-attr="data-turn-tree-context-menu"
    width-class="w-40"
    :width="160"
    :height="144"
    @select="handleContextAction"
    @close="closeContextMenu"
  />

  <div v-if="detailModalOpen" class="fixed inset-0 z-[86] flex items-center justify-center p-4" role="dialog" aria-modal="true">
    <div class="modal-overlay" @click="closeDetailModal"></div>
    <div class="modal-card relative flex w-full max-w-2xl flex-col overflow-hidden" @click.stop>
      <div class="modal-header flex-col items-start gap-1">
        <h3 class="text-base font-semibold text-[var(--color-text-main)]">Turn Details</h3>
        <p class="text-sm text-[var(--color-text-muted)]">Inspect the stored content and artifact summary for this turn.</p>
      </div>
      <div class="max-h-[65vh] space-y-4 overflow-y-auto px-5 py-4">
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
          <p class="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">Usage</p>
          <p class="mt-1 text-sm text-[var(--color-text-main)]" :title="detailUsageTooltip">{{ detailUsageLabel }}</p>
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
            <div v-for="artifact in detailArtifacts" :key="artifact.key" class="rounded-md border border-[var(--color-border)] px-3 py-2 text-sm" style="background-color: color-mix(in srgb, var(--color-surface) 62%, transparent);">
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
        <button type="button" class="btn-secondary px-3 py-2 text-sm" @click="closeDetailModal">Close</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { apiService } from '../../services/apiService'
import { formatTimestamp } from '../../utils/dateUtils'
import { formatUsageCompact, formatUsageTooltip } from '../../utils/usageFormat'
import FloatingActionMenu from '../ui/FloatingActionMenu.vue'

const emit = defineEmits(['select', 'mark-final', 'delete-turn'])
const actions = [
  { id: 'open', label: 'Open' },
  { id: 'mark-final', label: 'Mark Final' },
  { id: 'view-details', label: 'View Details' },
  { id: 'delete', label: 'Delete', destructive: true, dividerBefore: true },
]
const contextMenu = ref({ open: false, conversationId: '', turnId: '', x: 0, y: 0 })
const detailModalOpen = ref(false)
const detailTurn = ref(null)
const detailUsage = computed(() => detailTurn.value?.metadata?.token_usage || null)
const detailUsageLabel = computed(() => formatUsageCompact(detailUsage.value))
const detailUsageTooltip = computed(() => formatUsageTooltip(detailUsage.value))

const detailArtifacts = computed(() => {
  const events = Array.isArray(detailTurn.value?.tool_events) ? detailTurn.value.tool_events : []
  return events.filter((event) => event && event.type === 'artifact' && event.data).map((event, index) => {
    const artifact = event.data || {}
    const kind = String(artifact.kind || 'artifact')
    const label = String(artifact.display_name || artifact.logical_name || artifact.artifact_id || `artifact_${index + 1}`)
    const columns = Array.isArray(artifact.schema) ? artifact.schema.length : 0
    const rowCount = Number.isFinite(Number(artifact.row_count)) ? Number(artifact.row_count) : null
    const metaParts = []
    if (rowCount !== null) metaParts.push(`${rowCount} rows`)
    if (columns > 0) metaParts.push(`${columns} columns`)
    return { key: `${label}-${index}`, label, kind, meta: metaParts.join(' · ') }
  })
})

function open(payload) {
  const conversationId = String(payload?.conversationId || '').trim()
  const turnId = String(payload?.turnId || '').trim()
  if (!conversationId || !turnId) return
  contextMenu.value = { open: true, conversationId, turnId, x: Number(payload?.x || 0), y: Number(payload?.y || 0) }
}

function closeContextMenu() {
  contextMenu.value = { open: false, conversationId: '', turnId: '', x: 0, y: 0 }
}

async function handleContextAction(action) {
  const { conversationId, turnId } = contextMenu.value
  closeContextMenu()
  if (action === 'open') emit('select', { conversationId, turnId })
  else if (action === 'mark-final') emit('mark-final', { conversationId, turnId })
  else if (action === 'delete') emit('delete-turn', { conversationId, turnId })
  else if (action === 'view-details') {
    detailTurn.value = await apiService.v1GetTurn(conversationId, turnId)
    detailModalOpen.value = true
  }
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

onMounted(() => {
  document.addEventListener('keydown', handleEscape)
})
onUnmounted(() => {
  document.removeEventListener('keydown', handleEscape)
})

defineExpose({ open })
</script>
