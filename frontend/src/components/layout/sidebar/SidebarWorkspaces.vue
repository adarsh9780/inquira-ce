<template>
  <div class="flex flex-col w-full">
    <!-- Header -->
    <div 
      class="flex items-center justify-between px-3 py-2 group cursor-pointer transition-colors"
      :class="isCollapsed ? 'justify-center hover:bg-gray-200/50 rounded-lg mx-2 mb-1' : 'hover:bg-gray-200/50'"
      @click="$emit('header-click')"
      title="Workspaces"
    >
      <div class="flex items-center gap-2">
        <RectangleGroupIcon class="w-4 h-4 text-gray-500 transition-transform" :class="!isCollapsed && 'scale-110 text-gray-700'" />
        <span v-if="!isCollapsed" class="text-xs font-semibold text-gray-600 uppercase tracking-wider">Workspaces</span>
      </div>
      <button 
        v-if="!isCollapsed"
        @click.stop="openCreateDialog" 
        class="p-1 hover:bg-gray-300 rounded text-gray-500 transition-opacity"
        :class="appStore.workspaces.length > 0 ? 'opacity-0 group-hover:opacity-100' : 'opacity-100'"
        title="New Workspace"
      >
        <PlusIcon class="w-3.5 h-3.5" />
      </button>
    </div>

    <!-- List -->
    <div v-show="!isCollapsed" class="flex flex-col mt-0.5 space-y-0.5 px-2 pb-2">
      <div v-if="appStore.workspaceDeletionJobs.length > 0" class="px-2 py-1.5 bg-amber-50 text-amber-800 text-[11px] flex items-center gap-1.5 rounded">
        <svg class="animate-spin h-3 w-3 text-amber-700 shrink-0" viewBox="0 0 24 24" fill="none">
          <circle class="opacity-30" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-90" d="M22 12a10 10 0 0 1-10 10" stroke="currentColor" stroke-width="4" />
        </svg>
        <span class="truncate">Deleting workspace...</span>
      </div>

      <div v-if="appStore.workspaces.length === 0" class="px-2 py-2 text-xs text-center text-gray-400">
        No workspaces yet
      </div>
      
      <div 
        v-for="ws in appStore.workspaces" 
        :key="ws.id"
        class="group/item relative flex items-center justify-between px-2 py-1.5 rounded-md cursor-pointer transition-colors"
        :class="[
          ws.id === appStore.activeWorkspaceId ? 'bg-blue-50/50' : 'hover:bg-gray-200/50',
          isWorkspaceDeleting(ws.id) ? 'opacity-60 cursor-not-allowed' : ''
        ]"
        @click="!isWorkspaceDeleting(ws.id) && selectWorkspace(ws.id)"
      >
        <div class="flex items-center gap-2 min-w-0 pr-2">
          <CheckCircleIcon 
            v-if="ws.id === appStore.activeWorkspaceId" 
            class="w-3.5 h-3.5 text-green-500 shrink-0" 
          />
          <div v-else class="w-3.5 h-3.5 shrink-0"></div>
          <span class="truncate text-xs" :class="ws.id === appStore.activeWorkspaceId ? 'font-medium text-blue-800' : 'text-gray-700'">
            {{ ws.name }}
          </span>
        </div>
        
        <button
          v-if="!isWorkspaceDeleting(ws.id) && ws.id !== appStore.activeWorkspaceId"
          @click.stop="confirmDeleteWorkspace(ws.id)"
          class="p-1 rounded text-gray-400 hover:text-red-500 hover:bg-gray-200 opacity-0 group-hover/item:opacity-100 transition-opacity shrink-0"
          title="Delete Workspace"
        >
           <TrashIcon class="w-3.5 h-3.5" />
        </button>
      </div>
    </div>

    <!-- Modals -->
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
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useAppStore } from '../../../stores/appStore'
import { useAuthStore } from '../../../stores/authStore'
import { toast } from '../../../composables/useToast'
import { extractApiErrorMessage } from '../../../utils/apiError'
import WorkspaceCreateModal from '../../modals/WorkspaceCreateModal.vue'
import ConfirmationModal from '../../modals/ConfirmationModal.vue'
import { 
  RectangleGroupIcon, 
  PlusIcon,
  CheckCircleIcon,
  TrashIcon
} from '@heroicons/vue/24/outline'

const props = defineProps({
  isCollapsed: { type: Boolean, default: false }
})

const emit = defineEmits(['header-click', 'select'])

const appStore = useAppStore()
const authStore = useAuthStore()

const isCreateDialogOpen = ref(false)
const isCreatingWorkspace = ref(false)
const isDeleteDialogOpen = ref(false)
const pendingDeleteWorkspaceId = ref('')

async function selectWorkspace(id) {
  if (id === appStore.activeWorkspaceId) {
    emit('select')
    return
  }
  try {
    await appStore.activateWorkspace(id)
    await appStore.fetchConversations()
    if (appStore.activeConversationId) {
      await appStore.fetchConversationTurns({ reset: true })
    }
    emit('select')
  } catch (error) {
    toast.error('Workspace Error', error.message || 'Failed to activate workspace')
  }
}

function openCreateDialog() {
  // If clicked while collapsed, it will expand the sidebar via parent.
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
    const ws = await appStore.createWorkspace(name)
    await appStore.fetchWorkspaces()
    isCreateDialogOpen.value = false
    emit('select') // Auto collapse or just notify selection
    if (ws?.id) {
       await selectWorkspace(ws.id)
    }
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

onMounted(async () => {
  try {
    await appStore.fetchWorkspaces()
    await appStore.fetchWorkspaceDeletionJobs()
  } catch (e) {
    // ignore
  }
})
</script>
