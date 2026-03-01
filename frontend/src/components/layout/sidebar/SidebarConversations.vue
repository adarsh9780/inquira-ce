<template>
  <div class="flex flex-col w-full h-full min-h-[0]">
    <!-- Header -->
    <div 
      class="flex items-center justify-between px-3 py-2 group cursor-pointer transition-colors shrink-0"
      :class="[
        isCollapsed ? 'justify-center hover:bg-gray-200/50 rounded-lg mx-2 mb-1' : 'hover:bg-gray-200/50',
        !appStore.hasWorkspace ? 'opacity-50 cursor-not-allowed' : ''
      ]"
      @click="handleHeaderClick"
      title="Conversations"
    >
      <div class="flex items-center gap-2">
        <ChatBubbleLeftRightIcon class="w-4 h-4 text-gray-500 transition-transform" :class="!isCollapsed && 'scale-110 text-gray-700'" />
        <span v-if="!isCollapsed" class="text-xs font-semibold text-gray-600 uppercase tracking-wider">Conversations</span>
      </div>
      <button 
        v-if="!isCollapsed && appStore.hasWorkspace"
        @click.stop="createConversation" 
        class="p-1 hover:bg-gray-300 rounded text-gray-500 transition-opacity"
        :class="appStore.conversations.length > 0 ? 'opacity-0 group-hover:opacity-100' : 'opacity-100'"
        title="New Conversation"
      >
        <PlusIcon class="w-3.5 h-3.5" />
      </button>
    </div>

    <!-- List -->
    <div v-show="!isCollapsed && appStore.hasWorkspace" class="flex flex-col mt-0.5 space-y-0.5 px-2 pb-2 overflow-y-auto flex-1">
      <div v-if="appStore.conversations.length === 0" class="px-2 py-2 text-xs text-center text-gray-400">
        No conversations yet.
      </div>
      
      <div 
        v-for="conv in appStore.conversations" 
        :key="conv.id"
        class="group/item relative flex items-center justify-between px-2 py-1.5 rounded-md cursor-pointer transition-colors"
        :class="conv.id === appStore.activeConversationId ? 'bg-blue-50/50 border border-blue-100/50' : 'hover:bg-gray-200/50 border border-transparent'"
        @click="selectConversation(conv.id)"
      >
        <div class="flex items-start gap-2 min-w-0 pr-2 pt-0.5">
          <CheckCircleIcon 
            v-if="conv.id === appStore.activeConversationId" 
            class="w-3.5 h-3.5 text-green-500 shrink-0 mt-0.5" 
          />
          <div v-else class="w-3.5 h-3.5 shrink-0 mt-0.5"></div>
          <div class="flex-1 min-w-0">
             <p class="truncate text-xs" :class="conv.id === appStore.activeConversationId ? 'font-medium text-blue-800' : 'text-gray-700'">
              {{ conv.title || 'Conversation' }}
             </p>
             <p class="text-[9px] text-gray-400 truncate">{{ formatTimestamp(conv.updated_at || conv.created_at) }}</p>
          </div>
        </div>

        <button
          v-if="conv.id !== appStore.activeConversationId"
          @click.stop="deleteConv(conv.id)"
          class="p-1 rounded text-gray-400 hover:text-red-500 hover:bg-gray-200 opacity-0 group-hover/item:opacity-100 transition-opacity shrink-0"
          title="Delete Conversation"
        >
           <TrashIcon class="w-3 h-3" />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, watch, onMounted } from 'vue'
import { useAppStore } from '../../../stores/appStore'
import { apiService } from '../../../services/apiService'
import { formatTimestamp } from '../../../utils/dateUtils'
import { toast } from '../../../composables/useToast'
import { extractApiErrorMessage } from '../../../utils/apiError'
import { 
  ChatBubbleLeftRightIcon, 
  PlusIcon,
  CheckCircleIcon,
  TrashIcon
} from '@heroicons/vue/24/outline'

const props = defineProps({
  isCollapsed: { type: Boolean, default: false }
})

const emit = defineEmits(['header-click', 'select'])

const appStore = useAppStore()

function handleHeaderClick() {
  if (!appStore.hasWorkspace) return
  emit('header-click')
  if (props.isCollapsed) {
     appStore.fetchConversations()
  }
}

async function selectConversation(id) {
  if (id === appStore.activeConversationId) return
  try {
    appStore.setActiveConversationId(id)
    await appStore.fetchConversationTurns({ reset: true })
    emit('select') // We'll handle whether to close or not in parent
  } catch (error) {
    toast.error('Failed to load conversation', extractApiErrorMessage(error))
  }
}

async function createConversation() {
  try {
    await appStore.createConversation()
    await appStore.fetchConversationTurns({ reset: true })
    emit('select')
  } catch (error) {
    toast.error('Failed to create conversation', extractApiErrorMessage(error))
  }
}

async function deleteConv(id) {
  try {
    await apiService.v1DeleteConversation(id)
    const activeWasDeleted = id === appStore.activeConversationId
    
    // update local list
    appStore.conversations = appStore.conversations.filter(c => c.id !== id)
    
    if (activeWasDeleted) {
       appStore.setActiveConversationId(appStore.conversations[0]?.id || '')
       appStore.chatHistory = []
       appStore.turnsNextCursor = null
       if (appStore.activeConversationId) {
         await appStore.fetchConversationTurns({ reset: true })
       }
    }
  } catch (error) {
    toast.error('Failed to delete conversation', extractApiErrorMessage(error))
  }
}

watch(
  () => appStore.hasWorkspace,
  async (hasWorkspace) => {
    if (hasWorkspace && !props.isCollapsed) {
      await appStore.fetchConversations()
    }
  }
)

watch(
  () => props.isCollapsed,
  (collapsed) => {
    if (!collapsed && appStore.hasWorkspace) {
      appStore.fetchConversations()
    }
  }
)

onMounted(() => {
  if (!props.isCollapsed && appStore.hasWorkspace) {
    appStore.fetchConversations()
  }
})
</script>
