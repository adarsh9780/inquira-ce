<template>
  <div class="flex h-full min-w-0 bg-white rounded-xl overflow-hidden">
    <div class="flex-1 min-w-0 flex flex-col">
    <Teleport to="#workspace-left-pane-toolbar" v-if="isMounted && appStore.workspacePane === 'chat'">
      <div class="flex items-center w-full justify-end">
          <div class="flex items-center gap-1 bg-gray-50 p-1 rounded-xl border border-gray-100">
            <button
              type="button"
              class="flex items-center justify-center rounded-lg p-1.5 text-gray-600 hover:bg-white hover:text-blue-600 transition-all hover:shadow-sm"
              @click="createConversation"
              :disabled="!appStore.hasWorkspace"
              title="New Conversation"
            >
              <PlusIcon class="h-4 w-4" />
            </button>
            <div class="w-px h-4 bg-gray-200 mx-0.5"></div>
            <button
              type="button"
              class="flex items-center justify-center rounded-lg p-1.5 text-gray-600 hover:bg-white hover:text-amber-600 disabled:cursor-not-allowed disabled:opacity-40 transition-all hover:shadow-sm"
              :disabled="!appStore.activeConversationId"
              @click="clearConversation"
              title="Clear Conversation"
            >
              <ArrowPathIcon class="h-4 w-4" />
            </button>
            <button
              type="button"
              class="flex items-center justify-center rounded-lg p-1.5 text-gray-600 hover:bg-white hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-40 transition-all hover:shadow-sm"
              :disabled="!appStore.activeConversationId"
              @click="deleteConversation"
              title="Delete Conversation"
            >
              <TrashIcon class="h-4 w-4" />
            </button>
          </div>
      </div>
    </Teleport>

      <div class="flex-1 min-h-0 overflow-y-auto bg-gray-50/30" data-chat-scroll-container>
        <div v-if="!appStore.hasWorkspace" class="flex items-center justify-center h-full px-4 sm:px-6 lg:px-8 pt-4 sm:pt-6 lg:pt-8 pb-2 sm:pb-3 lg:pb-4">
          <div class="text-center max-w-md">
            <div class="mx-auto flex items-center justify-center h-16 w-16 sm:h-20 sm:w-20 rounded-2xl bg-gradient-to-br from-amber-100 to-orange-100 mb-4 sm:mb-6 shadow-lg">
              <ChatBubbleLeftRightIcon class="h-8 w-8 sm:h-10 sm:w-10 text-amber-700" />
            </div>
            <h3 class="text-xl sm:text-2xl font-bold text-gray-900 mb-2 sm:mb-3">Create a Workspace First</h3>
            <p class="text-sm sm:text-base text-gray-600 leading-relaxed">
              Open the workspace dropdown in the header and create your first workspace before starting analysis.
            </p>
          </div>
        </div>

        <div v-else-if="appStore.chatHistory.length === 0" class="flex items-center justify-center h-full px-4 sm:px-6 lg:px-8 pt-4 sm:pt-6 lg:pt-8 pb-2 sm:pb-3 lg:pb-4">
          <div class="text-center max-w-md">
            <div class="mx-auto flex items-center justify-center h-16 w-16 sm:h-20 sm:w-20 rounded-2xl bg-gradient-to-br from-blue-100 to-indigo-100 mb-4 sm:mb-6 shadow-lg">
              <ChatBubbleLeftRightIcon class="h-8 w-8 sm:h-10 sm:w-10 text-blue-600" />
            </div>
            <h3 class="text-xl sm:text-2xl font-bold text-gray-900 mb-2 sm:mb-3">Start Your Analysis</h3>
            <p class="text-sm sm:text-base text-gray-600 leading-relaxed">
              Point Inquira at your local dataset path, add your OpenRouter API key in Settings, then ask a question to generate code and insights.
            </p>
          </div>
        </div>

        <div v-else class="px-3 sm:px-4 pt-3 sm:pt-4 pb-2 sm:pb-3 space-y-3 sm:space-y-4">
          <ChatHistory />
        </div>
      </div>

      <div class="flex-shrink-0 border-t border-gray-100 bg-white pt-2 sm:pt-3">
        <ChatInput />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch, nextTick } from 'vue'
import { useAppStore } from '../../stores/appStore'
import ChatHistory from './ChatHistory.vue'
import ChatInput from './ChatInput.vue'
import { 
  ChatBubbleLeftRightIcon, 
  ArrowPathIcon,
  PlusIcon,
  TrashIcon
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

async function clearConversation() {
  if (!appStore.activeConversationId) return
  try {
    await appStore.clearActiveConversation()
  } catch (error) {
    toast.error('Conversation Error', extractApiErrorMessage(error, 'Failed to clear conversation'))
  }
}

async function deleteConversation() {
  if (!appStore.activeConversationId) return
  try {
    await appStore.deleteActiveConversation()
    if (appStore.activeConversationId) {
      await appStore.fetchConversationTurns({ reset: true })
    }
  } catch (error) {
    toast.error('Conversation Error', extractApiErrorMessage(error, 'Failed to delete conversation'))
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
