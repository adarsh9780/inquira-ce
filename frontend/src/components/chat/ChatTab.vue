<template>
  <div class="flex h-full min-w-0 rounded-xl overflow-hidden" style="background-color: var(--color-base);">
    <div class="flex-1 min-w-0 flex flex-col">
      <div class="chat-scroll-shell flex-1 min-h-0 overflow-y-auto" style="background-color: var(--color-base);" data-chat-scroll-container>
        <AppEmptyState
          v-if="!appStore.hasWorkspace"
          title="Select a workspace"
          description="Create or select a workspace before starting an analysis."
          action-label="Open workspace settings"
          @action="appStore.openSettings('workspace')"
        ><template #icon><ChatBubbleLeftRightIcon class="h-6 w-6" /></template></AppEmptyState>

        <AppEmptyState
          v-else-if="appStore.chatHistory.length === 0"
          title="Ask about your data"
          description="Use the composer below to generate an analysis, table, or chart."
        ><template #icon><ChatBubbleLeftRightIcon class="h-6 w-6" /></template></AppEmptyState>

        <div v-else class="px-2 sm:px-2 pt-2 pb-1 space-y-2">
          <ChatHistory />
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { onMounted, watch } from 'vue'
import { useAppStore } from '../../stores/appStore'
import ChatHistory from './ChatHistory.vue'
import AppEmptyState from '../ui/AppEmptyState.vue'
import { ChatBubbleLeftRightIcon } from '@heroicons/vue/24/outline'

const appStore = useAppStore()

onMounted(async () => {
  try {
    await appStore.fetchWorkspaces()
    if (!appStore.activeWorkspaceId) return
    await appStore.fetchConversations()
    if (!appStore.activeConversationId && appStore.conversations.length > 0) {
      appStore.setActiveConversationId(appStore.conversations[0].id)
    }
    if (appStore.activeConversationId) {
      await appStore.fetchConversationTurns({ reset: true })
    }
  } catch (error) {
    console.error('Failed to initialize workspace conversations:', error)
  }
})

watch(
  () => appStore.activeWorkspaceId,
  async (workspaceId) => {
    if (!workspaceId) return
    await appStore.fetchConversations()
    if (appStore.activeConversationId) {
      await appStore.fetchConversationTurns({ reset: true })
    }
  }
)
</script>

<style scoped>
.chat-scroll-shell {
  scrollbar-width: thin;
  scrollbar-color: color-mix(in srgb, var(--color-border) 68%, transparent) transparent;
}

.chat-scroll-shell::-webkit-scrollbar {
  width: 6px;
}

.chat-scroll-shell::-webkit-scrollbar-track {
  background: transparent;
}

.chat-scroll-shell::-webkit-scrollbar-thumb {
  border-radius: 9999px;
  background: color-mix(in srgb, var(--color-border) 62%, transparent);
}

.chat-scroll-shell::-webkit-scrollbar-thumb:hover {
  background: color-mix(in srgb, var(--color-border) 80%, transparent);
}
</style>
