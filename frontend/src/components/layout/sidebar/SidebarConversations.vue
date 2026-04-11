<template>
  <div class="flex flex-col w-full h-full min-h-[0]">
    <div
      class="flex items-center justify-between w-full py-2 transition-colors shrink-0"
      :class="!appStore.hasWorkspace ? 'opacity-50 cursor-not-allowed' : 'hover:bg-zinc-100/60'"
      @click="toggleExpanded"
    >
      <div class="flex items-center gap-2 min-w-0">
        <ChevronRightIcon
          class="w-3.5 h-3.5 shrink-0 transition-transform duration-200"
          :class="isExpanded ? 'rotate-90' : ''"
          style="color: var(--color-text-muted);"
        />
        <ChatBubbleLeftRightIcon class="w-3.5 h-3.5 shrink-0" style="color: var(--color-text-muted);" />
        <span class="text-[11px] uppercase tracking-[0.08em] font-semibold" style="color: var(--color-text-muted);">
          Conversations
        </span>
      </div>
      <button
        v-if="appStore.hasWorkspace"
        @click.stop="createConversation"
        class="btn-icon shrink-0"
        title="New Conversation"
      >
        <PlusIcon class="w-3.5 h-3.5" />
      </button>
    </div>

    <Transition name="sidebar-list">
      <div v-show="isExpanded && appStore.hasWorkspace" class="flex flex-col mt-1 space-y-0.5 pl-4 pb-2 overflow-y-auto flex-1">
        <div
          v-if="appStore.conversations.length === 0"
          class="px-2 py-3 text-xs"
          style="color: var(--color-text-muted);"
        >
          No conversations yet. Start one for this workspace.
        </div>

        <button
          v-for="conv in appStore.conversations"
          :key="conv.id"
          type="button"
          class="group/item relative flex items-center justify-between rounded-lg px-2 py-1.5 text-left transition-colors text-xs"
          :class="conv.id === appStore.activeConversationId ? 'bg-[var(--color-accent-soft)] text-[var(--color-accent-text)]' : 'text-zinc-600 hover:bg-zinc-100/60 hover:text-zinc-800'"
          @click="selectConversation(conv.id)"
        >
          <div class="flex items-start gap-2 min-w-0 pr-2 pt-0.5 flex-1" @dblclick="startEditing(conv)">
            <ChatBubbleLeftRightIcon class="w-3.5 h-3.5 shrink-0 mt-0.5" :class="conv.id === appStore.activeConversationId ? 'text-[var(--color-accent-text)]' : 'text-zinc-400'" />
            <div class="flex-1 min-w-0">
              <div v-if="editingId === conv.id" class="flex items-center gap-1 w-full relative z-10">
                <input
                  :ref="(el) => { if (el) editInputs[conv.id] = el }"
                  v-model="editingTitleValue"
                  class="input-base py-0.5 px-1 text-xs font-semibold"
                  @keydown.enter.prevent="saveTitle(conv.id)"
                  @keydown.esc.prevent="cancelEditing"
                  @blur="saveTitle(conv.id)"
                  @click.stop
                />
              </div>
              <template v-else>
                <p
                  class="truncate"
                  :class="conv.id === appStore.activeConversationId ? 'font-semibold text-[var(--color-accent-text)]' : 'font-medium text-zinc-600'"
                  :title="conv.title || 'Conversation'"
                >
                  {{ conv.title || 'Conversation' }}
                </p>
                <p class="text-[9px] truncate" :class="conv.id === appStore.activeConversationId ? 'text-[var(--color-accent-text)] opacity-80' : 'text-zinc-400'">
                  {{ formatTimestamp(conv.updated_at || conv.created_at) }}
                </p>
              </template>
            </div>
          </div>

          <div v-if="editingId !== conv.id" class="flex-shrink-0 flex items-center opacity-0 group-hover/item:opacity-100 transition-opacity">
            <button
              @click.stop="startEditing(conv)"
              class="btn-icon p-1 hover:text-[var(--color-accent)]"
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
        </button>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { watch, onMounted, ref } from 'vue'
import { useAppStore } from '../../../stores/appStore'
import { apiService } from '../../../services/apiService'
import { formatTimestamp } from '../../../utils/dateUtils'
import { toast } from '../../../composables/useToast'
import { extractApiErrorMessage } from '../../../utils/apiError'
import {
  ChevronRightIcon,
  ChatBubbleLeftRightIcon,
  PlusIcon,
  TrashIcon,
  PencilIcon
} from '@heroicons/vue/24/outline'

defineProps({
  isCollapsed: { type: Boolean, default: false }
})

const emit = defineEmits(['header-click', 'select'])

const appStore = useAppStore()

const editingId = ref(null)
const editingTitleValue = ref('')
const editInputs = ref({})
const isExpanded = ref(true)

function startEditing(conv) {
  editingId.value = conv.id
  editingTitleValue.value = conv.title || 'Conversation'
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

  if (!newTitle || newTitle === (conv?.title || 'Conversation')) {
    cancelEditing()
    return
  }

  try {
    if (id === appStore.activeConversationId) {
      await appStore.updateConversationTitle(newTitle)
    } else {
      const updated = await apiService.v1UpdateConversation(id, newTitle)
      const idx = appStore.conversations.findIndex((c) => c.id === id)
      if (idx !== -1) {
        appStore.conversations[idx] = { ...appStore.conversations[idx], title: updated.title }
      }
    }
    toast.success('Renamed', 'Conversation title updated')
  } catch (error) {
    toast.error('Rename Failed', extractApiErrorMessage(error, 'Failed to update title'))
  } finally {
    cancelEditing()
  }
}

function toggleExpanded() {
  if (!appStore.hasWorkspace) return
  isExpanded.value = !isExpanded.value
  if (isExpanded.value) {
    emit('header-click')
    void appStore.fetchConversations()
  }
}

async function selectConversation(id) {
  if (id === appStore.activeConversationId) {
    emit('select')
    return
  }
  try {
    appStore.setActiveConversationId(id)
    await appStore.fetchConversationTurns({ reset: true })
    emit('select')
  } catch (error) {
    toast.error('Failed to load conversation', extractApiErrorMessage(error))
  }
}

async function createConversation() {
  try {
    await appStore.createConversation()
    await appStore.fetchConversationTurns({ reset: true })
    isExpanded.value = true
    emit('select')
  } catch (error) {
    toast.error('Failed to create conversation', extractApiErrorMessage(error))
  }
}

async function deleteConv(id) {
  try {
    await apiService.v1DeleteConversation(id)
    await appStore.fetchConversations()
    if (appStore.activeConversationId) {
      await appStore.fetchConversationTurns({ reset: true })
    }
  } catch (error) {
    toast.error('Failed to delete conversation', extractApiErrorMessage(error))
  }
}

watch(
  () => appStore.hasWorkspace,
  async (hasWorkspace) => {
    if (hasWorkspace && isExpanded.value) {
      await appStore.fetchConversations()
    }
  }
)

watch(
  () => appStore.activeWorkspaceId,
  async () => {
    if (!appStore.hasWorkspace) return
    isExpanded.value = true
    await appStore.fetchConversations()
  }
)

onMounted(() => {
  if (appStore.hasWorkspace && isExpanded.value) {
    void appStore.fetchConversations()
  }
})
</script>

<style scoped>
.sidebar-list-enter-active,
.sidebar-list-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.sidebar-list-enter-from,
.sidebar-list-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
