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
        <button class="text-xs px-2 py-1 rounded bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent-hover)]" @click="openWorkspaceSettings">New</button>
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
        <div
          v-for="ws in appStore.workspaces"
          :key="ws.id"
          class="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 flex items-center justify-between cursor-pointer"
          :class="[
            ws.id === appStore.activeWorkspaceId ? 'bg-[var(--color-accent-soft)]' : '',
            isWorkspaceDeleting(ws.id) ? 'opacity-60 cursor-not-allowed' : ''
          ]"
          @click="!isWorkspaceDeleting(ws.id) && activateWorkspace(ws.id)"
          @contextmenu.prevent="!isWorkspaceDeleting(ws.id) && openWorkspaceContextMenu($event, ws.id)"
        >
          <span class="truncate" :class="isWorkspaceDeleting(ws.id) ? 'text-gray-400' : ''">{{ ws.name }}</span>
          <button
            @click.stop="confirmDeleteWorkspace(ws.id)"
            class="text-xs text-red-500 hover:text-red-600 disabled:opacity-40"
            :disabled="isWorkspaceDeleting(ws.id)"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  </div>

  <div
    v-if="isWorkspaceContextMenuOpen"
    ref="contextMenuRef"
    class="fixed z-[80] w-56 rounded-lg border border-gray-200 bg-white shadow-xl py-1"
    :style="{ left: `${workspaceContextMenuX}px`, top: `${workspaceContextMenuY}px` }"
  >
    <button
      class="w-full text-left px-3 py-2 text-sm hover:bg-gray-50"
      @click="openRenameDialogFromContext"
    >
      Rename Workspace
    </button>
    <button
      class="w-full text-left px-3 py-2 text-sm hover:bg-gray-50"
      @click="confirmClearWorkspaceFromContext"
    >
      Clear Workspace Database
    </button>
    <button
      class="w-full text-left px-3 py-2 text-sm text-red-600 hover:bg-red-50"
      @click="confirmDeleteWorkspaceFromContext"
    >
      Delete Workspace
    </button>
  </div>

  <SettingsModal
    v-model="isSettingsOpen"
    :initial-tab="settingsInitialTab"
    :initial-step="settingsInitialStep"
  />

  <WorkspaceRenameModal
    :is-open="isRenameDialogOpen"
    :is-submitting="isRenamingWorkspace"
    :initial-name="pendingRenameWorkspaceName"
    @close="closeRenameDialog"
    @submit="renameWorkspace"
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

  <ConfirmationModal
    :is-open="isClearDbDialogOpen"
    title="Clear Workspace Database"
    :message="clearDbDialogMessage"
    confirm-text="Clear Database"
    cancel-text="Cancel"
    @close="closeClearDbDialog"
    @confirm="clearWorkspaceDatabase"
  />
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useAppStore } from '../stores/appStore'
import { toast } from '../composables/useToast'
import { extractApiErrorMessage } from '../utils/apiError'
import SettingsModal from './modals/SettingsModal.vue'
import WorkspaceRenameModal from './modals/WorkspaceRenameModal.vue'
import ConfirmationModal from './modals/ConfirmationModal.vue'

const appStore = useAppStore()
const isOpen = ref(false)
const containerRef = ref(null)
const isSettingsOpen = ref(false)
const settingsInitialTab = ref('workspace')
const settingsInitialStep = ref(1)
const isDeleteDialogOpen = ref(false)
const pendingDeleteWorkspaceId = ref('')
const isClearDbDialogOpen = ref(false)
const pendingClearDbWorkspaceId = ref('')
const isRenameDialogOpen = ref(false)
const isRenamingWorkspace = ref(false)
const pendingRenameWorkspaceId = ref('')
const pendingRenameWorkspaceName = ref('')
const isWorkspaceContextMenuOpen = ref(false)
const workspaceContextMenuX = ref(0)
const workspaceContextMenuY = ref(0)
const contextWorkspaceId = ref('')
const contextMenuRef = ref(null)

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

function openWorkspaceSettings() {
  closeWorkspaceContextMenu()
  isOpen.value = false
  settingsInitialTab.value = 'workspace'
  settingsInitialStep.value = 1
  isSettingsOpen.value = true
}

function isWorkspaceDeleting(workspaceId) {
  return appStore.workspaceDeletionJobs.some((job) => job.workspace_id === workspaceId)
}

function confirmDeleteWorkspace(workspaceId) {
  closeWorkspaceContextMenu()
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

function openWorkspaceContextMenu(event, workspaceId) {
  const targetId = String(workspaceId || '')
  if (!targetId) return
  contextWorkspaceId.value = targetId
  workspaceContextMenuX.value = Number(event?.clientX || 0)
  workspaceContextMenuY.value = Number(event?.clientY || 0)
  isWorkspaceContextMenuOpen.value = true
}

function closeWorkspaceContextMenu() {
  isWorkspaceContextMenuOpen.value = false
  contextWorkspaceId.value = ''
}

function openRenameDialogFromContext() {
  const workspaceId = contextWorkspaceId.value
  const ws = appStore.workspaces.find((item) => item.id === workspaceId)
  closeWorkspaceContextMenu()
  if (!workspaceId || !ws) return
  pendingRenameWorkspaceId.value = workspaceId
  pendingRenameWorkspaceName.value = ws.name || ''
  isRenameDialogOpen.value = true
}

function closeRenameDialog() {
  if (isRenamingWorkspace.value) return
  isRenameDialogOpen.value = false
  pendingRenameWorkspaceId.value = ''
  pendingRenameWorkspaceName.value = ''
}

async function renameWorkspace(name) {
  const workspaceId = pendingRenameWorkspaceId.value
  if (!workspaceId || !name) return
  isRenamingWorkspace.value = true
  try {
    await appStore.renameWorkspace(workspaceId, name)
    toast.success('Workspace Updated', 'Workspace name updated successfully.')
    closeRenameDialog()
  } catch (error) {
    toast.error('Workspace Error', extractApiErrorMessage(error, 'Failed to rename workspace'))
  } finally {
    isRenamingWorkspace.value = false
  }
}

function confirmClearWorkspaceFromContext() {
  const workspaceId = contextWorkspaceId.value
  closeWorkspaceContextMenu()
  if (!workspaceId) return
  pendingClearDbWorkspaceId.value = workspaceId
  isClearDbDialogOpen.value = true
}

function closeClearDbDialog() {
  isClearDbDialogOpen.value = false
  pendingClearDbWorkspaceId.value = ''
}

const clearDbDialogMessage = computed(() => {
  const target = appStore.workspaces.find((ws) => ws.id === pendingClearDbWorkspaceId.value)
  const name = target?.name || 'this workspace'
  return `Clear ${name} database and scratchpad artifacts? You will need to re-select the original dataset to rebuild workspace data.`
})

async function clearWorkspaceDatabase() {
  const workspaceId = pendingClearDbWorkspaceId.value
  if (!workspaceId) return
  try {
    const result = await appStore.clearWorkspaceDatabase(workspaceId)
    toast.success('Workspace Database Cleared', result?.detail || 'Workspace database cleared.')
    closeClearDbDialog()
  } catch (error) {
    toast.error('Workspace Error', extractApiErrorMessage(error, 'Failed to clear workspace database'))
  }
}

function confirmDeleteWorkspaceFromContext() {
  const workspaceId = contextWorkspaceId.value
  closeWorkspaceContextMenu()
  if (!workspaceId) return
  confirmDeleteWorkspace(workspaceId)
}

function handleClickOutside(event) {
  const clickedOutsideDropdown = containerRef.value && !containerRef.value.contains(event.target)
  const clickedOutsideContextMenu = contextMenuRef.value && !contextMenuRef.value.contains(event.target)
  if (clickedOutsideDropdown) {
    isOpen.value = false
  }
  if (clickedOutsideContextMenu) {
    closeWorkspaceContextMenu()
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
