<template>
  <div class="flex h-full min-w-0 rounded-xl overflow-hidden" style="background-color: var(--color-base);">
    <div class="flex-1 min-w-0 flex flex-col">
      <div class="chat-scroll-shell flex-1 min-h-0 overflow-y-auto" style="background-color: var(--color-base);" data-chat-scroll-container>
        <AppEmptyState
          v-if="appStore.workspaceReadiness.state === 'no_workspace'"
          title="Create your first workspace"
          description="A workspace keeps your data, conversations, and AI preferences together."
          action-label="Create workspace"
          @action="appStore.openSettings('workspace')"
        ><template #icon><ChatBubbleLeftRightIcon class="h-6 w-6" /></template></AppEmptyState>

        <AppEmptyState
          v-else-if="appStore.workspaceReadiness.state === 'no_data'"
          title="Add data to begin"
          description="Drop a CSV, Excel, JSON, or Parquet file anywhere in the window, or choose files."
          action-label="Choose files"
          @action="openDatasetPicker"
        ><template #icon><CircleStackIcon class="h-6 w-6" /></template></AppEmptyState>

        <AppEmptyState
          v-else-if="appStore.workspaceReadiness.state === 'model_connection_required'"
          title="Connect a model"
          description="Provider credentials are saved once and used by your workspaces."
          action-label="Connect model"
          @action="appStore.openSettings('llm')"
        ><template #icon><KeyIcon class="h-6 w-6" /></template></AppEmptyState>

        <AppEmptyState
          v-else-if="appStore.workspaceReadiness.state === 'workspace_configuration_required'"
          title="Review workspace AI"
          description="Choose workspace models and confirm its data-sharing permission."
          action-label="Review configuration"
          @action="appStore.openSettings('workspace')"
        ><template #icon><SparklesIcon class="h-6 w-6" /></template></AppEmptyState>

        <AppEmptyState
          v-else-if="appStore.chatHistory.length === 0"
          title="Ask about your data"
          description="Start with a common analysis or write your own question below."
        >
          <template #icon><ChatBubbleLeftRightIcon class="h-6 w-6" /></template>
          <div class="mt-4 flex max-w-md flex-wrap justify-center gap-2">
            <button v-for="prompt in starterPrompts" :key="prompt" type="button" class="rounded-full border border-[var(--color-border)] px-3 py-1.5 text-xs text-[var(--color-text-sub)] transition-colors hover:border-[var(--color-border-hover)] hover:bg-[var(--color-base-soft)]" @click="appStore.currentQuestion = prompt">{{ prompt }}</button>
          </div>
        </AppEmptyState>

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
import { ChatBubbleLeftRightIcon, CircleStackIcon, KeyIcon, SparklesIcon } from '@heroicons/vue/24/outline'

const appStore = useAppStore()
const starterPrompts = ['Summarize this dataset', 'Check for missing values', 'Show the main trends', 'Find unusual records']
function openDatasetPicker() {
  window.dispatchEvent(new CustomEvent('inquira:open-dataset-picker'))
}

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
