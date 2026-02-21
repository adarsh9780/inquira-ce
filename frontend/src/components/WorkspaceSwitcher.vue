<template>
  <div ref="containerRef" class="relative">
    <button
      @click="toggleOpen"
      class="flex items-center space-x-2 px-3 py-2 text-sm bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
    >
      <span class="font-medium text-gray-700">Workspace:</span>
      <span class="max-w-[180px] truncate">{{ activeWorkspaceName || 'Select Workspace' }}</span>
      <svg class="w-4 h-4 text-gray-400" :class="{ 'rotate-180': isOpen }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>

    <div v-if="isOpen" class="absolute top-full left-0 mt-1 w-80 bg-white rounded-lg shadow-lg border border-gray-200 z-50 overflow-hidden">
      <div class="p-2 border-b border-gray-100 flex justify-between items-center">
        <span class="text-xs text-gray-500">Workspaces</span>
        <button class="text-xs px-2 py-1 rounded bg-blue-600 text-white hover:bg-blue-700" @click="createWorkspace">New</button>
      </div>

      <div v-if="appStore.workspaces.length === 0" class="p-3 text-sm text-center text-gray-500">No workspaces yet</div>
      <div v-else class="max-h-64 overflow-auto">
        <button
          v-for="ws in appStore.workspaces"
          :key="ws.id"
          class="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 flex items-center justify-between"
          :class="ws.id === appStore.activeWorkspaceId ? 'bg-blue-50' : ''"
          @click="activateWorkspace(ws.id)"
        >
          <span class="truncate">{{ ws.name }}</span>
          <button
            v-if="appStore.workspaces.length > 1"
            @click.stop="deleteWorkspace(ws.id)"
            class="text-xs text-red-500 hover:text-red-600"
          >
            Delete
          </button>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useAppStore } from '../stores/appStore'
import { toast } from '../composables/useToast'
import { apiService } from '../services/apiService'

const appStore = useAppStore()
const isOpen = ref(false)
const containerRef = ref(null)

const activeWorkspaceName = computed(() => {
  const active = appStore.workspaces.find((w) => w.id === appStore.activeWorkspaceId)
  return active?.name || ''
})

function toggleOpen() {
  isOpen.value = !isOpen.value
}

async function activateWorkspace(workspaceId) {
  try {
    await appStore.activateWorkspace(workspaceId)
    await appStore.fetchConversations()
    if (appStore.activeConversationId) {
      await appStore.fetchConversationTurns({ reset: true })
    }
    isOpen.value = false
  } catch (error) {
    toast.error('Workspace Error', error.message || 'Failed to activate workspace')
  }
}

async function createWorkspace() {
  const name = window.prompt('Workspace name')
  if (!name) return
  try {
    await appStore.createWorkspace(name)
    await appStore.fetchWorkspaces()
  } catch (error) {
    toast.error('Workspace Error', error.message || 'Failed to create workspace')
  }
}

async function deleteWorkspace(workspaceId) {
  if (!window.confirm('Delete this workspace permanently?')) return
  try {
    await apiService.v1DeleteWorkspace(workspaceId)
    await appStore.fetchWorkspaces()
  } catch (error) {
    toast.error('Workspace Error', error.message || 'Failed to delete workspace')
  }
}

function handleClickOutside(event) {
  if (containerRef.value && !containerRef.value.contains(event.target)) {
    isOpen.value = false
  }
}

onMounted(async () => {
  document.addEventListener('click', handleClickOutside)
  try {
    await appStore.fetchWorkspaces()
    if (appStore.workspaces.length === 0) {
      await appStore.createWorkspace('Default Workspace')
      await appStore.fetchWorkspaces()
    }
  } catch (_error) {
    // ignore on initial load when v1 isn't configured yet
  }
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>
