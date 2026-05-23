<template>
  <div
    :class="variant === 'page'
      ? 'min-h-0 flex-1 overflow-y-auto px-1 py-3'
      : 'mt-1 space-y-1 pl-3 pr-1 pb-2'"
  >
    <div v-if="isLoading" :class="variant === 'page' ? 'px-2 py-6 text-sm text-[var(--color-text-muted)]' : 'px-2 py-2 text-[11px] text-[var(--color-text-muted)]'">
      Loading tree...
    </div>
    <div v-else-if="conversations.length === 0" :class="variant === 'page' ? 'px-2 py-6 text-sm text-[var(--color-text-muted)]' : 'px-2 py-2 text-[11px] text-[var(--color-text-muted)]'">
      No conversation turns yet.
    </div>
    <div v-else :class="variant === 'page' ? 'space-y-2 py-2' : 'space-y-2'">
      <div
        v-for="conversation in conversations"
        :key="conversation.id"
        class="space-y-1"
      >
        <button
          type="button"
          :class="variant === 'page'
            ? 'flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-[13px] font-medium text-[var(--color-text-main)] transition-colors hover:bg-[var(--color-text-main)]/5'
            : 'flex w-full items-center gap-1.5 rounded-md px-2 py-1 text-left text-[12px] font-medium text-[var(--color-text-main)] transition-colors hover:bg-[var(--color-text-main)]/5'"
          :title="conversation.title || 'Untitled'"
          @click="selectConversation(conversation.id)"
        >
          <ChevronRightIcon
            class="h-3 w-3 shrink-0 transition-transform"
            :class="isExpanded(conversation.id) ? 'rotate-90' : ''"
          />
          <span class="truncate">{{ conversation.title || 'Untitled' }}</span>
        </button>
        <div v-show="isExpanded(conversation.id)" :class="variant === 'page' ? 'ml-4 border-l border-[var(--color-border)] pl-3' : 'ml-2 border-l border-[var(--color-border)] pl-2'">
          <SidebarTreeNode
            v-for="node in conversation.roots || []"
            :key="node.id"
            :node="node"
            :active-turn-id="appStore.activeTurnId"
            @select="selectTurn(conversation.id, $event)"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, onMounted, ref, watch } from 'vue'
import { ChevronRightIcon } from '@heroicons/vue/24/outline'
import { useAppStore } from '../../../stores/appStore'
import { toast } from '../../../composables/useToast'
import { extractApiErrorMessage } from '../../../utils/apiError'

const appStore = useAppStore()
defineProps({
  variant: { type: String, default: 'sidebar' },
})
const isLoading = ref(false)
const expandedConversationIds = ref(new Set())

const conversations = computed(() => {
  const raw = appStore.workspaceTurnTree?.conversations
  return Array.isArray(raw) ? raw : []
})

const SidebarTreeNode = defineComponent({
  name: 'SidebarTreeNode',
  props: {
    node: { type: Object, required: true },
    activeTurnId: { type: String, default: '' },
  },
  emits: ['select'],
  setup(props, { emit }) {
    const collapsed = ref(false)
    return () => {
      const children = Array.isArray(props.node?.children) ? props.node.children : []
      const hasChildren = children.length > 0
      const isActive = String(props.activeTurnId || '').trim() === String(props.node?.id || '').trim()
      return h('div', { class: 'space-y-1 py-0.5' }, [
        h('div', { class: 'flex items-start gap-1' }, [
          hasChildren
            ? h('button', {
                type: 'button',
                class: 'mt-1 flex h-3 w-3 shrink-0 items-center justify-center text-[var(--color-text-muted)]',
                title: collapsed.value ? 'Expand replies' : 'Collapse replies',
                onClick: (event) => {
                  event.stopPropagation()
                  collapsed.value = !collapsed.value
                },
              }, collapsed.value ? '+' : '-')
            : h('span', { class: 'h-3 w-3 shrink-0' }),
          h('button', {
            type: 'button',
            class: [
              'min-w-0 flex-1 rounded px-1.5 py-1 text-left text-[11px] transition-colors',
              isActive
                ? 'bg-[var(--color-selected-surface)] text-[var(--color-text-main)]'
                : 'text-[var(--color-text-muted)] hover:bg-[var(--color-text-main)]/5 hover:text-[var(--color-text-main)]',
            ],
            title: String(props.node?.user_text || '').trim(),
            onClick: () => emit('select', String(props.node?.id || '').trim()),
          }, [
            h('span', { class: 'block truncate' }, String(props.node?.user_text || '').trim() || `Turn ${props.node?.seq_no || ''}`.trim()),
          ]),
        ]),
        hasChildren && !collapsed.value
          ? h('div', { class: 'ml-3 border-l border-[var(--color-border)] pl-2' }, children.map((child) => h(SidebarTreeNode, {
              key: child.id,
              node: child,
              activeTurnId: props.activeTurnId,
              onSelect: (turnId) => emit('select', turnId),
            })))
          : null,
      ])
    }
  },
})

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

async function refreshTree() {
  if (!appStore.activeWorkspaceId) return
  isLoading.value = true
  try {
    await appStore.loadWorkspaceTurnTree()
    const next = new Set(expandedConversationIds.value)
    for (const conversation of conversations.value) {
      if (conversation.id === appStore.activeConversationId) next.add(conversation.id)
    }
    expandedConversationIds.value = next
  } catch (error) {
    toast.error('Tree load failed', extractApiErrorMessage(error, 'Unable to load conversation tree.'))
  } finally {
    isLoading.value = false
  }
}

async function selectConversation(conversationId) {
  toggleConversation(conversationId)
}

async function selectTurn(conversationId, turnId) {
  const targetConversationId = String(conversationId || '').trim()
  const targetTurnId = String(turnId || '').trim()
  if (!targetConversationId || !targetTurnId) return
  try {
    if (targetConversationId !== appStore.activeConversationId) {
      appStore.setActiveConversationId(targetConversationId)
      await appStore.fetchConversationTurns({ reset: true })
    }
    await appStore.loadActiveTurnRelations(targetTurnId)
    appStore.setActiveTab('workspace')
    toggleConversation(targetConversationId, true)
  } catch (error) {
    toast.error('Turn load failed', extractApiErrorMessage(error, 'Unable to open this turn.'))
  }
}

onMounted(() => {
  void refreshTree()
})

watch(() => appStore.activeWorkspaceId, () => {
  expandedConversationIds.value = new Set()
  void refreshTree()
})

watch(() => appStore.activeConversationId, (conversationId) => {
  if (conversationId) toggleConversation(conversationId, true)
})
</script>
