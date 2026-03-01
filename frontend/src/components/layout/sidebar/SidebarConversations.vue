<template>
  <div class="flex flex-col w-full h-full min-h-[0]">
    <!-- Header -->
    <div 
      class="flex items-center justify-between px-3 py-2 group cursor-pointer transition-colors shrink-0"
      :class="[
        isCollapsed ? 'justify-center hover:bg-zinc-100/50 rounded-lg mx-2 mb-1' : 'hover:bg-zinc-100/50',
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
        class="btn-icon transition-opacity"
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
        class="group/item relative flex items-center justify-between px-2 py-1.5 rounded-md cursor-pointer transition-colors border"
        :class="conv.id === appStore.activeConversationId ? 'bg-zinc-100/80 border-zinc-200' : 'border-transparent hover:bg-zinc-100/50'"
        @click="selectConversation(conv.id)"
      >
        <div class="flex items-start gap-2 min-w-0 pr-2 pt-0.5" @dblclick="startEditing(conv)">
          <CheckCircleIcon 
            v-if="conv.id === appStore.activeConversationId" 
            class="w-3.5 h-3.5 text-green-500 shrink-0 mt-0.5" 
          />
          <div v-else class="w-3.5 h-3.5 shrink-0 mt-0.5"></div>
          <div class="flex-1 min-w-0">
             <div v-if="editingId === conv.id" class="flex items-center gap-1 w-full relative z-10">
               <input
                 :ref="(el) => { if (el) editInputs[conv.id] = el }"
                 v-model="editingTitleValue"
                 class="w-full bg-white px-1 py-0.5 text-xs font-semibold text-gray-900 border border-blue-400 rounded focus:outline-none focus:ring-1 focus:ring-blue-500 shadow-sm"
                 @keydown.enter.prevent="saveTitle(conv.id)"
                 @keydown.esc.prevent="cancelEditing"
                 @blur="saveTitle(conv.id)"
                 @click.stop
               />
             </div>
             <template v-else>
               <p 
                 class="truncate text-xs" 
                 :class="conv.id === appStore.activeConversationId ? 'font-medium text-blue-800' : 'text-gray-700'"
                 :title="conv.title || 'Conversation'"
               >
                 {{ conv.title || 'Conversation' }}
               </p>
               <p class="text-[9px] text-gray-400 truncate">{{ formatTimestamp(conv.updated_at || conv.created_at) }}</p>
             </template>
          </div>
        </div>

        <div v-if="editingId !== conv.id" class="flex-shrink-0 flex items-center opacity-0 group-hover/item:opacity-100 transition-opacity">
          <button
            @click.stop="startEditing(conv)"
            class="btn-icon p-1 hover:text-blue-600"
            title="Rename Conversation"
          >
             <PencilIcon class="w-3 h-3" />
          </button>
          <button
            v-if="conv.id !== appStore.activeConversationId"
            @click.stop="deleteConv(conv.id)"
            class="btn-icon p-1 hover:text-red-500"
            title="Delete Conversation"
          >
             <TrashIcon class="w-3 h-3" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, watch, onMounted, ref } from 'vue'
import { useAppStore } from '../../../stores/appStore'
import { apiService } from '../../../services/apiService'
import { formatTimestamp } from '../../../utils/dateUtils'
import { toast } from '../../../composables/useToast'
import { extractApiErrorMessage } from '../../../utils/apiError'
import { 
  ChatBubbleLeftRightIcon, 
  PlusIcon,
  CheckCircleIcon,
  TrashIcon,
  PencilIcon
} from '@heroicons/vue/24/outline'

const props = defineProps({
  isCollapsed: { type: Boolean, default: false }
})

const emit = defineEmits(['header-click', 'select'])

const appStore = useAppStore()

// Inline Editing
const editingId = ref(null)
const editingTitleValue = ref('')
const editInputs = ref({})

function startEditing(conv) {
  editingId.value = conv.id
  editingTitleValue.value = conv.title || 'Conversation'
  // Focus next tick
  setTimeout(() => {
    const inputEl = editInputs.value[conv.id]
    if (inputEl) {
      inputEl.focus()
      inputEl.select()
    }
  }, 50)
}

function cancelEditing() {
  editingId.value = null
  editingTitleValue.value = ''
}

async function saveTitle(id) {
  if (editingId.value !== id) return
  
  const newTitle = editingTitleValue.value.trim()
  const conv = appStore.conversations.find((c) => c.id === id)
  
  // No change or empty
  if (!newTitle || newTitle === (conv?.title || 'Conversation')) {
    cancelEditing()
    return
  }

  try {
    // If the renamed conversation is the active one, we can use the appStore's method
    if (id === appStore.activeConversationId) {
      await appStore.updateConversationTitle(newTitle)
    } else {
      // Otherwise, hit the API directly and mutate the list
      await apiService.v1UpdateConversation(id, { title: newTitle })
      if (conv) conv.title = newTitle
    }
    toast.success('Renamed', 'Conversation title updated')
  } catch (error) {
    toast.error('Rename Failed', extractApiErrorMessage(error, 'Failed to update title'))
  } finally {
    cancelEditing()
  }
}

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
