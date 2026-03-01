<template>
  <div class="flex h-full min-w-0 bg-white rounded-xl overflow-hidden">
    <div class="flex-1 min-w-0 flex flex-col">
    <Teleport to="#workspace-left-pane-toolbar" v-if="isMounted && appStore.workspacePane === 'chat'">
      <div class="flex items-center w-full gap-4 justify-between">
        <div class="flex-1 min-w-0 flex items-center gap-2 group">
          <div v-if="!isEditingTitle" class="min-w-0 flex items-center gap-2 overflow-hidden">
            <h3 
              class="min-w-0 truncate text-sm font-bold text-gray-900 cursor-pointer hover:text-blue-600 transition-colors"
              @click="startEditingTitle"
              title="Click to rename"
            >
              {{ activeConversationTitle }}
            </h3>
            <button 
              @click="startEditingTitle" 
              class="opacity-0 group-hover:opacity-100 p-1 hover:bg-gray-100 rounded-md transition-all flex-shrink-0"
              title="Rename conversation"
            >
              <PencilIcon class="h-3 w-3 text-gray-400" />
            </button>
          </div>
          <div v-else class="flex-1 max-w-sm flex items-center gap-2">
            <input
              ref="titleInputRef"
              v-model="editingTitleValue"
              class="w-full px-2 py-1 text-sm font-bold text-gray-900 border border-blue-500 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-100 bg-blue-50/30"
              @keydown.enter="saveTitle"
              @keydown.esc="cancelEditingTitle"
              @blur="saveTitle"
            />
          </div>
        </div>

        <div class="ml-auto flex items-center gap-1 sm:gap-1.5 flex-shrink-0">
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
            <div class="w-px h-4 bg-gray-200 mx-0.5"></div>
            <button
              type="button"
              class="flex items-center justify-center rounded-lg p-1.5 text-gray-600 hover:bg-white hover:text-blue-600 transition-all hover:shadow-sm"
              @click="openConversationHistory"
              title="Conversation history"
            >
              <ClockIcon class="h-4 w-4" />
            </button>
          </div>
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

  <ConversationHistoryModal
    :is-open="isConversationHistoryOpen"
    :conversations="appStore.conversations"
    :active-conversation-id="appStore.activeConversationId"
    @close="isConversationHistoryOpen = false"
    @select="selectConversationFromHistory"
  />
</template>

<script setup>
import { computed, onMounted, ref, watch, nextTick } from 'vue'
import { useAppStore } from '../../stores/appStore'
import ChatHistory from './ChatHistory.vue'
import ChatInput from './ChatInput.vue'
import ConversationHistoryModal from './ConversationHistoryModal.vue'
import { 
  ChatBubbleLeftRightIcon, 
  ArrowPathIcon, 
  ClockIcon, 
  PlusIcon, 
  TrashIcon,
  PencilIcon
} from '@heroicons/vue/24/outline'
import { toast } from '../../composables/useToast'
import { extractApiErrorMessage } from '../../utils/apiError'

const appStore = useAppStore()
const isConversationHistoryOpen = ref(false)
const isMounted = ref(false)

// Title Editing
const isEditingTitle = ref(false)
const editingTitleValue = ref('')
const titleInputRef = ref(null)

const activeConversationTitle = computed(() => {
  const active = appStore.conversations.find((conv) => conv.id === appStore.activeConversationId)
  return active?.title || 'New Conversation'
})

function startEditingTitle() {
  if (!appStore.activeConversationId) return
  editingTitleValue.value = activeConversationTitle.value
  isEditingTitle.value = true
  nextTick(() => {
    titleInputRef.value?.focus()
    titleInputRef.value?.select()
  })
}

function cancelEditingTitle() {
  isEditingTitle.value = false
}

async function saveTitle() {
  if (!isEditingTitle.value) return
  const newTitle = editingTitleValue.value.trim()
  
  if (!newTitle || newTitle === activeConversationTitle.value) {
    isEditingTitle.value = false
    return
  }

  try {
    await appStore.updateConversationTitle(newTitle)
    isEditingTitle.value = false
    toast.success('Renamed', 'Conversation title updated')
  } catch (error) {
    toast.error('Rename Failed', extractApiErrorMessage(error, 'Failed to update title'))
  }
}

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
