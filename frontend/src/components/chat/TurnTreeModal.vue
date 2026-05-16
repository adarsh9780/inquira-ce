<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 layer-modal overflow-y-auto"
    role="dialog"
    aria-modal="true"
  >
    <div class="modal-overlay" @click="closeModal"></div>

    <div class="flex min-h-full items-center justify-center p-4">
      <div class="modal-card relative w-full max-w-3xl" @click.stop>
        <div class="modal-header flex-col items-start gap-1">
          <h3 class="text-base font-semibold text-[var(--color-text-main)]">Conversation Tree</h3>
          <p class="text-sm text-[var(--color-text-muted)]">Open any turn to restore the chat and artifact state for that node.</p>
        </div>

        <div class="max-h-[70vh] overflow-y-auto px-5 py-4">
          <div v-if="roots.length === 0" class="rounded-lg border border-dashed border-[var(--color-border)] px-4 py-8 text-center text-sm text-[var(--color-text-muted)]">
            No turns yet.
          </div>
          <div v-else class="space-y-3">
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
import { computed, defineComponent, h, onMounted, onUnmounted } from 'vue'
import { formatTimestamp } from '../../utils/dateUtils'

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

const TurnTreeBranch = defineComponent({
  name: 'TurnTreeBranch',
  props: {
    node: {
      type: Object,
      required: true
    },
    currentTurnId: {
      type: String,
      default: ''
    },
    finalTurnId: {
      type: String,
      default: ''
    }
  },
  emits: ['select', 'mark-final'],
  setup(branchProps, { emit: branchEmit }) {
    const isCurrent = computed(() => String(branchProps.currentTurnId || '').trim() === String(branchProps.node?.id || '').trim())
    const isFinal = computed(() => String(branchProps.finalTurnId || '').trim() === String(branchProps.node?.id || '').trim())
    const label = computed(() => {
      const raw = String(branchProps.node?.user_text || '').trim()
      return raw || `Turn ${branchProps.node?.seq_no || ''}`.trim()
    })
    const childNodes = computed(() => (Array.isArray(branchProps.node?.children) ? branchProps.node.children : []))

    const handleSelect = () => {
      branchEmit('select', branchProps.node?.id)
    }

    return () =>
      h('div', { class: 'space-y-3' }, [
        h(
          'div',
          {
            class: 'rounded-xl border px-4 py-3 transition-colors',
            style: {
              borderColor: isCurrent.value ? 'var(--color-border-hover)' : 'var(--color-border)',
              backgroundColor: isCurrent.value
                ? 'color-mix(in srgb, var(--color-accent) 8%, var(--color-base))'
                : 'transparent',
            },
          },
          [
            h('div', { class: 'flex items-start justify-between gap-3' }, [
              h('div', { class: 'min-w-0 flex-1' }, [
                h('div', { class: 'flex flex-wrap items-center gap-2' }, [
                  h('span', { class: 'text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--color-text-muted)]' }, `Node ${branchProps.node?.seq_no || ''}`),
                  h('span', { class: 'text-[11px] text-[var(--color-text-muted)]' }, String(branchProps.node?.id || '')),
                  isCurrent.value
                    ? h('span', {
                        class: 'rounded-full border px-2 py-0.5 text-[10px] font-semibold',
                        style: { borderColor: 'var(--color-border)', color: 'var(--color-accent)' }
                      }, 'Current')
                    : null,
                  isFinal.value
                    ? h('span', {
                        class: 'rounded-full border px-2 py-0.5 text-[10px] font-semibold',
                        style: { borderColor: 'var(--color-border)', color: 'var(--color-accent)' }
                      }, 'Final')
                    : null,
                ]),
                h('p', { class: 'mt-2 line-clamp-2 text-sm font-medium text-[var(--color-text-main)]' }, label.value),
                h('p', { class: 'mt-1 text-xs text-[var(--color-text-muted)]' }, formatTimestamp(branchProps.node?.created_at)),
              ]),
              h('div', { class: 'flex shrink-0 items-center gap-2' }, [
                h(
                  'button',
                  {
                    type: 'button',
                    class: 'rounded-lg border px-2 py-1 text-xs font-medium transition-colors hover:bg-[var(--color-base-soft)]',
                    style: { borderColor: 'var(--color-border)', color: 'var(--color-text-main)' },
                    onClick: handleSelect,
                  },
                  'Open'
                ),
                h(
                  'button',
                  {
                    type: 'button',
                    class: 'rounded-lg border px-2 py-1 text-xs font-medium transition-colors hover:bg-[var(--color-base-soft)]',
                    style: { borderColor: 'var(--color-border)', color: 'var(--color-text-main)' },
                    onClick: () => branchEmit('mark-final', branchProps.node?.id),
                  },
                  'Mark Final'
                ),
              ]),
            ])
          ]
        ),
        childNodes.value.length
          ? h(
              'div',
              { class: 'ml-5 border-l border-[var(--color-border)] pl-4 space-y-3' },
              childNodes.value.map((child) =>
                h(TurnTreeBranch, {
                  key: child.id,
                  node: child,
                  currentTurnId: branchProps.currentTurnId,
                  finalTurnId: branchProps.finalTurnId,
                  onSelect: (turnId) => branchEmit('select', turnId),
                  onMarkFinal: (turnId) => branchEmit('mark-final', turnId),
                })
              )
            )
          : null,
      ])
  }
})

onMounted(() => {
  document.addEventListener('keydown', handleEscape)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleEscape)
})
</script>
