<template>
  <div class="flex h-full bg-white rounded-xl overflow-hidden">
    <div class="w-64 border-r border-gray-100 flex flex-col bg-gray-50/70">
      <div class="p-3 border-b border-gray-100 flex items-center justify-between">
        <h3 class="text-sm font-semibold text-gray-700">Conversations</h3>
        <button class="text-xs px-2 py-1 rounded bg-blue-600 text-white hover:bg-blue-700" @click="createConversation">
          New
        </button>
      </div>
      <div class="flex-1 overflow-auto p-2 space-y-1">
        <button
          v-for="conv in appStore.conversations"
          :key="conv.id"
          class="w-full text-left px-2 py-2 rounded text-sm"
          :class="conv.id === appStore.activeConversationId ? 'bg-blue-100 text-blue-800' : 'hover:bg-gray-100 text-gray-700'"
          @click="selectConversation(conv.id)"
        >
          <p class="font-medium truncate">{{ conv.title || 'Conversation' }}</p>
        </button>
      </div>
      <div class="p-2 border-t border-gray-100 flex gap-2">
        <button class="text-xs px-2 py-1 rounded bg-amber-100 text-amber-800 hover:bg-amber-200" @click="clearConversation">
          Clear
        </button>
        <button class="text-xs px-2 py-1 rounded bg-red-100 text-red-700 hover:bg-red-200" @click="deleteConversation">
          Delete
        </button>
      </div>
    </div>

    <div class="flex-1 flex flex-col">
      <!-- Chat History -->
      <div class="flex-1 overflow-y-auto bg-gray-50/30" data-chat-scroll-container>
        <div v-if="appStore.chatHistory.length === 0" class="flex items-center justify-center h-full px-4 sm:px-6 lg:px-8 pt-4 sm:pt-6 lg:pt-8 pb-2 sm:pb-3 lg:pb-4">
          <div class="text-center max-w-md">
            <div class="mx-auto flex items-center justify-center h-16 w-16 sm:h-20 sm:w-20 rounded-2xl bg-gradient-to-br from-blue-100 to-indigo-100 mb-4 sm:mb-6 shadow-lg">
              <ChatBubbleLeftRightIcon class="h-8 w-8 sm:h-10 sm:w-10 text-blue-600" />
            </div>
            <h3 class="text-xl sm:text-2xl font-bold text-gray-900 mb-2 sm:mb-3">Start Your Analysis</h3>
            <p class="text-sm sm:text-base text-gray-600 leading-relaxed">
              Point Inquira at your local dataset path, add your Gemini API key in Settings, then ask a question to generate code and insights.
            </p>
          </div>
        </div>

        <div v-else class="px-3 sm:px-4 pt-3 sm:pt-4 pb-2 sm:pb-3 space-y-3 sm:space-y-4">
          <ChatHistory />
        </div>
      </div>

      <!-- Chat Input -->
      <div class="flex-shrink-0 border-t border-gray-100 bg-white pt-2 sm:pt-3">
        <ChatInput />
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, watch } from 'vue'
import { useAppStore } from '../../stores/appStore'
import ChatHistory from './ChatHistory.vue'
import ChatInput from './ChatInput.vue'
import { ChatBubbleLeftRightIcon } from '@heroicons/vue/24/outline'
import { toast } from '../../composables/useToast'

const appStore = useAppStore()

async function createConversation() {
  try {
    await appStore.createConversation()
    await appStore.fetchConversationTurns({ reset: true })
  } catch (error) {
    toast.error('Conversation Error', error.message || 'Failed to create conversation')
  }
}

async function selectConversation(conversationId) {
  appStore.setActiveConversationId(conversationId)
  await appStore.fetchConversationTurns({ reset: true })
}

async function clearConversation() {
  if (!appStore.activeConversationId) return
  await appStore.clearActiveConversation()
}

async function deleteConversation() {
  if (!appStore.activeConversationId) return
  await appStore.deleteActiveConversation()
  if (appStore.activeConversationId) {
    await appStore.fetchConversationTurns({ reset: true })
  }
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
