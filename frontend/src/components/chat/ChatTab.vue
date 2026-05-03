<template>
  <div class="flex h-full min-w-0 rounded-xl overflow-hidden" style="background-color: var(--color-base);">
    <div class="flex-1 min-w-0 flex flex-col">
    <Teleport to="#workspace-left-pane-toolbar" v-if="isMounted && appStore.workspacePane === 'chat'">
      <div class="flex items-center w-full justify-end">
          <div
            class="flex items-center gap-1 rounded-xl border p-1"
            style="background-color: var(--color-control-surface); border-color: var(--color-border);"
          >
            <button
              type="button"
              class="btn-icon hover:text-[var(--color-accent)]"
              style="--chat-toolbar-selected-surface: var(--color-selected-surface);"
              @click="createConversation"
              :disabled="!appStore.hasWorkspace"
              title="New Conversation"
            >
              <PlusIcon class="h-4 w-4" />
            </button>
          </div>
      </div>
    </Teleport>

      <div class="chat-scroll-shell flex-1 min-h-0 overflow-y-auto" style="background-color: var(--color-base);" data-chat-scroll-container>
        <div v-if="!appStore.hasWorkspace" class="flex items-center justify-center h-full px-4 sm:px-6 lg:px-8 pt-4 sm:pt-6 lg:pt-8 pb-2 sm:pb-3 lg:pb-4">
          <div class="text-center max-w-md">
            <div
              class="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl shadow-lg sm:mb-6 sm:h-20 sm:w-20"
              style="background: linear-gradient(135deg, color-mix(in srgb, var(--color-accent) 20%, var(--color-base)) 0%, color-mix(in srgb, var(--color-chart-accent) 18%, var(--color-base)) 100%);"
            >
              <ChatBubbleLeftRightIcon class="h-8 w-8 sm:h-10 sm:w-10" style="color: var(--color-accent-text);" />
            </div>
            <h3 class="text-xl sm:text-2xl font-bold mb-2 sm:mb-3" style="color: var(--color-text-main);">Create a Workspace First</h3>
            <p class="text-sm sm:text-base leading-relaxed" style="color: var(--color-text-muted);">
              Open the workspace dropdown in the header and create your first workspace before starting analysis.
            </p>
          </div>
        </div>

        <div v-else-if="appStore.chatHistory.length === 0" class="flex items-center justify-center h-full px-4 sm:px-6 lg:px-8 pt-4 sm:pt-6 lg:pt-8 pb-2 sm:pb-3 lg:pb-4">
          <div class="text-center max-w-md">
            <div
              class="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl shadow-lg sm:mb-6 sm:h-20 sm:w-20"
              style="background: linear-gradient(135deg, color-mix(in srgb, var(--color-chart-accent) 20%, var(--color-base)) 0%, color-mix(in srgb, var(--color-accent) 16%, var(--color-base)) 100%);"
            >
              <ChatBubbleLeftRightIcon class="h-8 w-8 sm:h-10 sm:w-10" style="color: var(--color-chart-accent);" />
            </div>
            <h3 class="text-xl sm:text-2xl font-bold mb-2 sm:mb-3" style="color: var(--color-text-main);">Start Your Analysis</h3>
            <p class="text-sm sm:text-base leading-relaxed" style="color: var(--color-text-muted);">
              Point Inquira at your local dataset path, add your OpenRouter API key in Settings, then ask a question to generate code and insights.
            </p>
          </div>
        </div>

        <div v-else class="px-2 sm:px-2 pt-2 pb-1 space-y-2">
          <ChatHistory />
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { useAppStore } from '../../stores/appStore'
import ChatHistory from './ChatHistory.vue'
import { 
  ChatBubbleLeftRightIcon, 
  PlusIcon
} from '@heroicons/vue/24/outline'
import { toast } from '../../composables/useToast'
import { extractApiErrorMessage } from '../../utils/apiError'

const appStore = useAppStore()
const isMounted = ref(false)

async function createConversation() {
  try {
    await appStore.createConversation()
    await appStore.fetchConversationTurns({ reset: true })
  } catch (error) {
    toast.error('Conversation Error', extractApiErrorMessage(error, 'Failed to create conversation'))
  }
}

onMounted(async () => {
  isMounted.value = true
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
