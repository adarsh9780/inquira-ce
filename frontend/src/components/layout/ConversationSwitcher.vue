<template>
  <HeaderDropdown
    :model-value="conversationStore.activeConversationId || null"
    :options="conversationOptions"
    :open="uiStore.isConversationSwitcherOpen"
    :trigger-label="activeConversationTitle"
    :disabled="!workspaceStore.hasWorkspace || selecting"
    trigger-variant="breadcrumb"
    max-width-class="max-w-64"
    aria-label="Switch conversation"
    placeholder="New conversation"
    searchable
    search-placeholder="Search conversations"
    no-results-label="No conversations found"
    :max-options-without-search="11"
    :dropdown-min-width="288"
    @update:open="uiStore.setConversationSwitcherOpen"
    @update:model-value="selectConversation"
  />
</template>

<script setup lang="ts">
import { computed, markRaw, ref } from 'vue'
import { PlusIcon } from '@heroicons/vue/24/outline'
import { useConversationStore } from '../../stores/conversationStore'
import { useUiStore } from '../../stores/uiStore'
import { useWorkspaceStore } from '../../stores/workspaceStore'
import { toast } from '../../composables/useToast'
import { extractApiErrorMessage } from '../../utils/apiError'
import { formatCompactRelativeTimestamp } from '../../utils/dateUtils'
import HeaderDropdown from '../ui/HeaderDropdown.vue'

const NEW_CONVERSATION = '__new_conversation__'
const conversationStore = useConversationStore()
const uiStore = useUiStore()
const workspaceStore = useWorkspaceStore()
const selecting = ref(false)

const activeConversationTitle = computed(() => {
  const id = String(conversationStore.activeConversationId || '').trim()
  if (!id) return 'New conversation'
  const conversation = conversationStore.conversations.find((item) => String(item?.id || '') === id)
  return String(conversation?.title || '').trim() || 'Untitled conversation'
})

const conversationOptions = computed(() => [
  {
    value: NEW_CONVERSATION,
    label: 'New conversation',
    description: 'Start with a blank analysis',
    icon: markRaw(PlusIcon),
    tags: ['new', 'analysis'],
  },
  ...conversationStore.conversations.map((conversation) => {
    const timestamp = conversation.last_turn_at || conversation.updated_at || conversation.created_at
    const relative = formatCompactRelativeTimestamp(timestamp)
    return {
      value: String(conversation.id),
      label: String(conversation.title || '').trim() || 'Untitled conversation',
      description: relative ? `Last active ${relative}` : 'No activity yet',
    }
  }),
])

async function selectConversation(value: string | number | null) {
  const target = String(value || '').trim()
  if (!target || selecting.value) return
  uiStore.closeConversationSwitcher()
  uiStore.setWorkspacePane('chat')

  if (target === NEW_CONVERSATION) {
    conversationStore.startConversationDraft()
    return
  }

  selecting.value = true
  try {
    conversationStore.setActiveConversationId(target)
    await conversationStore.fetchConversationTurns({ conversationId: target, preferLatest: true })
  } catch (error: unknown) {
    toast.error('Conversation Error', extractApiErrorMessage(error, 'Failed to load conversation'))
  } finally {
    selecting.value = false
  }
}
</script>
