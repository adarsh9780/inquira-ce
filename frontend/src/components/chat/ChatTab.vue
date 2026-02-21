<template>
  <div class="flex h-full bg-white rounded-xl overflow-hidden">
    <div class="flex-1 flex flex-col">
      <div class="border-b border-gray-100 bg-white px-3 py-2 sm:px-4">
        <div class="flex items-center justify-between gap-2">
          <div class="min-w-0">
            <p class="text-[11px] uppercase tracking-wide text-gray-500">Conversation</p>
            <h3 class="truncate text-sm font-semibold text-gray-800">{{ activeConversationTitle }}</h3>
          </div>
          <div class="flex items-center gap-2">
            <button
              type="button"
              class="rounded-md border border-gray-300 px-2 py-1 text-xs text-gray-700 hover:bg-gray-50"
              @click="createConversation"
            >
              New
            </button>
            <button
              type="button"
              class="rounded-md border border-amber-300 bg-amber-50 px-2 py-1 text-xs text-amber-800 hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="!appStore.activeConversationId"
              @click="clearConversation"
            >
              Clear
            </button>
            <button
              type="button"
              class="rounded-md border border-red-300 bg-red-50 px-2 py-1 text-xs text-red-700 hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="!appStore.activeConversationId"
              @click="deleteConversation"
            >
              Delete
            </button>
            <button
              type="button"
              class="rounded-md border border-gray-300 px-2 py-1 text-xs text-gray-700 hover:bg-gray-50"
              title="Conversation history"
              @click="openConversationHistory"
            >
              <span class="relative inline-block h-4 w-4 align-middle">
                <ArrowPathIcon class="h-4 w-4 text-gray-500" />
                <ClockIcon class="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full bg-white text-gray-500" />
              </span>
            </button>
          </div>
        </div>
      </div>

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

      <div class="flex-shrink-0 border-t border-gray-100 bg-white pt-2 sm:pt-3">
        <ChatInput />
      </div>
    </div>
  </div>

  <ConversationHistoryModal
    :is-open="isConversationHistoryOpen"
    :conversations="appStore.conversations"
    :active-conversation-id="appStore.activeConversationId"
    @close="isConversationHistoryOpen = false"
    @select="selectConversationFromHistory"
  />
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useAppStore } from '../../stores/appStore'
import ChatHistory from './ChatHistory.vue'
import ChatInput from './ChatInput.vue'
import ConversationHistoryModal from './ConversationHistoryModal.vue'
import { ChatBubbleLeftRightIcon, ArrowPathIcon, ClockIcon } from '@heroicons/vue/24/outline'
import { toast } from '../../composables/useToast'
import { extractApiErrorMessage } from '../../utils/apiError'

const appStore = useAppStore()
const isConversationHistoryOpen = ref(false)

const activeConversationTitle = computed(() => {
  const active = appStore.conversations.find((conv) => conv.id === appStore.activeConversationId)
  return active?.title || 'New Conversation'
})

async function createConversation() {
  try {
    await appStore.createConversation()
    await appStore.fetchConversationTurns({ reset: true })
  } catch (error) {
    toast.error('Conversation Error', extractApiErrorMessage(error, 'Failed to create conversation'))
  }
}

async function selectConversation(conversationId) {
  appStore.setActiveConversationId(conversationId)
  await appStore.fetchConversationTurns({ reset: true })
}

async function selectConversationFromHistory(conversationId) {
  await selectConversation(conversationId)
  isConversationHistoryOpen.value = false
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

async function openConversationHistory() {
  try {
    if (appStore.activeWorkspaceId) {
      await appStore.fetchConversations()
    }
  } catch (_error) {
    // Keep dialog usable with already loaded list.
  }
  isConversationHistoryOpen.value = true
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
