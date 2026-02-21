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
        <button class="text-xs px-2 py-1 rounded bg-blue-600 text-white hover:bg-blue-700" @click="openCreateDialog">New</button>
      </div>

      <div v-if="appStore.workspaceDeletionJobs.length > 0" class="px-3 py-2 border-b border-gray-100 bg-amber-50 text-amber-800 text-xs flex items-center space-x-2">
        <svg class="animate-spin h-3.5 w-3.5 text-amber-700" viewBox="0 0 24 24" fill="none">
          <circle class="opacity-30" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-90" d="M22 12a10 10 0 0 1-10 10" stroke="currentColor" stroke-width="4" />
        </svg>
        <span>Deleting...</span>
      </div>

      <div v-if="appStore.workspaces.length === 0" class="p-3 text-sm text-center text-gray-500">No workspaces yet</div>
      <div v-else class="max-h-64 overflow-auto">
        <button
          v-for="ws in appStore.workspaces"
          :key="ws.id"
          class="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 flex items-center justify-between"
          :class="ws.id === appStore.activeWorkspaceId ? 'bg-blue-50' : ''"
          :disabled="isWorkspaceDeleting(ws.id)"
          @click="activateWorkspace(ws.id)"
        >
          <span class="truncate" :class="isWorkspaceDeleting(ws.id) ? 'text-gray-400' : ''">{{ ws.name }}</span>
          <button
            @click.stop="confirmDeleteWorkspace(ws.id)"
            class="text-xs text-red-500 hover:text-red-600 disabled:opacity-40"
            :disabled="isWorkspaceDeleting(ws.id)"
          >
            Delete
          </button>
        </button>
      </div>
    </div>
  </div>

  <WorkspaceCreateModal
    :is-open="isCreateDialogOpen"
    :is-submitting="isCreatingWorkspace"
    :plan="authStore.planLabel"
    @close="closeCreateDialog"
    @submit="createWorkspace"
  />

  <ConfirmationModal
    :is-open="isDeleteDialogOpen"
    title="Delete Workspace"
    :message="deleteDialogMessage"
    confirm-text="Delete"
    cancel-text="Cancel"
    @close="closeDeleteDialog"
    @confirm="deleteWorkspace"
  />
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useAppStore } from '../stores/appStore'
import { useAuthStore } from '../stores/authStore'
import { toast } from '../composables/useToast'
import { extractApiErrorMessage } from '../utils/apiError'
import WorkspaceCreateModal from './modals/WorkspaceCreateModal.vue'
import ConfirmationModal from './modals/ConfirmationModal.vue'

const appStore = useAppStore()
const authStore = useAuthStore()
const isOpen = ref(false)
const containerRef = ref(null)
const isCreateDialogOpen = ref(false)
const isCreatingWorkspace = ref(false)
const isDeleteDialogOpen = ref(false)
const pendingDeleteWorkspaceId = ref('')

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

function openCreateDialog() {
  isOpen.value = false
  isCreateDialogOpen.value = true
}

function closeCreateDialog() {
  if (isCreatingWorkspace.value) return
  isCreateDialogOpen.value = false
}

async function createWorkspace(name) {
  if (!name) return
  isCreatingWorkspace.value = true
  try {
    await appStore.createWorkspace(name)
    await appStore.fetchWorkspaces()
    isCreateDialogOpen.value = false
    isOpen.value = false
  } catch (error) {
    toast.error('Workspace Error', extractApiErrorMessage(error, 'Failed to create workspace'))
  } finally {
    isCreatingWorkspace.value = false
  }
}

function isWorkspaceDeleting(workspaceId) {
  return appStore.workspaceDeletionJobs.some((job) => job.workspace_id === workspaceId)
}

function confirmDeleteWorkspace(workspaceId) {
  pendingDeleteWorkspaceId.value = workspaceId
  isDeleteDialogOpen.value = true
}

function closeDeleteDialog() {
  isDeleteDialogOpen.value = false
  pendingDeleteWorkspaceId.value = ''
}

const deleteDialogMessage = computed(() => {
  const target = appStore.workspaces.find((ws) => ws.id === pendingDeleteWorkspaceId.value)
  const name = target?.name || 'this workspace'
  return `Are you sure you want to delete ${name}? Cleanup will run in the background and cannot be undone.`
})

async function deleteWorkspace() {
  const workspaceId = pendingDeleteWorkspaceId.value
  if (!workspaceId) return
  try {
    const job = await appStore.deleteWorkspaceAsync(workspaceId)
    toast.info('Workspace Deletion Started', `Deleting workspace in background (job: ${job.job_id.slice(0, 8)}...).`)
    closeDeleteDialog()
  } catch (error) {
    toast.error('Workspace Error', extractApiErrorMessage(error, 'Failed to delete workspace'))
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
    await appStore.fetchWorkspaceDeletionJobs()
  } catch (_error) {
    // ignore on initial load when v1 isn't configured yet
  }
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>
