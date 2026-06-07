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

    <TurnTreeNodeActions
      ref="nodeActionsRef"
      @select="emit('select', $event)"
      @mark-final="emit('mark-final', $event)"
      @delete-turn="emit('delete-turn', $event)"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ChevronRightIcon } from '@heroicons/vue/24/outline'
import TurnTreeBranch from './TurnTreeBranch.vue'
import TurnTreeNodeActions from './TurnTreeNodeActions.vue'

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
const nodeActionsRef = ref(null)
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
  nodeActionsRef.value?.open({ conversationId, ...payload })
}

onMounted(() => {
  if (props.showConversationHeaders) {
    for (const conversation of normalizedConversations.value) {
      if (conversation.roots.length > 0) toggleConversation(conversation.id, true)
    }
  }
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
