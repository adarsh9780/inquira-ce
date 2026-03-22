<template>
  <div class="flex flex-col w-full">
    <div class="flex items-center justify-between py-2">
      <div class="flex items-center gap-2 min-w-0">
        <BuildingOffice2Icon class="w-3.5 h-3.5 shrink-0" style="color: var(--color-text-muted);" />
        <span class="text-[11px] uppercase tracking-[0.08em] font-semibold" style="color: var(--color-text-muted);">
          Workspace
        </span>
      </div>
      <button
        @click.stop="openCreateDialog"
        class="btn-icon shrink-0"
        title="New Workspace"
      >
        <PlusIcon class="w-3.5 h-3.5" />
      </button>
    </div>

    <div class="pb-2">
      <div v-if="appStore.workspaceDeletionJobs.length > 0" class="mb-2 px-2.5 py-2 bg-amber-50 text-amber-800 text-[11px] flex items-center gap-1.5 rounded-xl">
        <svg class="animate-spin h-3 w-3 text-amber-700 shrink-0" viewBox="0 0 24 24" fill="none">
          <circle class="opacity-30" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-90" d="M22 12a10 10 0 0 1-10 10" stroke="currentColor" stroke-width="4" />
        </svg>
        <span class="truncate">Workspace deletion in progress...</span>
      </div>

      <div
        v-if="appStore.workspaces.length === 0"
        class="px-1 py-3 text-xs"
        style="color: var(--color-text-muted);"
      >
        No workspaces yet. Create one to start organizing datasets and conversations.
      </div>

      <Listbox v-else :model-value="selectedWorkspaceId" @update:model-value="selectWorkspace">
        <div class="relative">
          <ListboxButton
            class="w-full rounded-lg px-3 py-2.5 text-left transition-colors hover:bg-zinc-100/60"
            style="background-color: color-mix(in srgb, var(--color-surface) 62%, transparent);"
          >
            <div class="flex items-center gap-3 min-w-0">
              <div class="min-w-0 flex-1">
                <p class="text-sm font-medium truncate" style="color: var(--color-text-main);">
                  {{ activeWorkspaceName }}
                </p>
              </div>
              <ChevronUpDownIcon class="w-4 h-4 shrink-0" style="color: var(--color-text-muted);" />
            </div>
          </ListboxButton>

          <transition name="workspace-dropdown">
            <ListboxOptions
              class="absolute z-30 mt-2 max-h-72 w-full overflow-auto rounded-xl border p-1 shadow-xl focus:outline-none"
              style="border-color: color-mix(in srgb, var(--color-border) 82%, transparent); background-color: var(--color-base);"
            >
              <ListboxOption
                v-for="ws in appStore.workspaces"
                :key="ws.id"
                :value="ws.id"
                as="template"
                v-slot="{ active, selected }"
                :disabled="isWorkspaceDeleting(ws.id)"
              >
                <li
                  class="group/item flex items-center justify-between gap-2 rounded-lg px-3 py-2 transition-colors"
                  :class="[
                    active ? 'bg-zinc-100/80' : '',
                    selected ? 'bg-emerald-50 text-emerald-800' : '',
                    isWorkspaceDeleting(ws.id) ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'
                  ]"
                >
                  <div class="flex items-center gap-2 min-w-0 flex-1">
                    <CheckCircleIcon v-if="selected" class="w-4 h-4 shrink-0 text-emerald-600" />
                    <BuildingOffice2Icon v-else class="w-4 h-4 shrink-0" style="color: var(--color-text-muted);" />
                    <span class="truncate text-sm" :class="selected ? 'font-semibold' : 'font-medium'">{{ ws.name }}</span>
                  </div>
                  <button
                    v-if="!isWorkspaceDeleting(ws.id)"
                    @click.stop="confirmDeleteWorkspace(ws.id)"
                    class="btn-icon p-1 text-zinc-400 hover:text-red-500 opacity-0 group-hover/item:opacity-100 transition-opacity shrink-0"
                    title="Delete Workspace"
                  >
                    <TrashIcon class="w-3.5 h-3.5" />
                  </button>
                </li>
              </ListboxOption>
            </ListboxOptions>
          </transition>
        </div>
      </Listbox>
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
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { Listbox, ListboxButton, ListboxOption, ListboxOptions } from '@headlessui/vue'
import { useAppStore } from '../../../stores/appStore'
import { useAuthStore } from '../../../stores/authStore'
import { toast } from '../../../composables/useToast'
import { extractApiErrorMessage } from '../../../utils/apiError'
import WorkspaceCreateModal from '../../modals/WorkspaceCreateModal.vue'
import ConfirmationModal from '../../modals/ConfirmationModal.vue'
import {
  BuildingOffice2Icon,
  CheckCircleIcon,
  ChevronUpDownIcon,
  PlusIcon,
  TrashIcon
} from '@heroicons/vue/24/outline'

defineProps({
  isCollapsed: { type: Boolean, default: false }
})

const emit = defineEmits(['header-click', 'select'])

const appStore = useAppStore()
const authStore = useAuthStore()

const isCreateDialogOpen = ref(false)
const isCreatingWorkspace = ref(false)
const isDeleteDialogOpen = ref(false)
const pendingDeleteWorkspaceId = ref('')

const selectedWorkspaceId = computed(() => String(appStore.activeWorkspaceId || '').trim())
const activeWorkspaceName = computed(() => {
  const activeId = selectedWorkspaceId.value
  const activeWorkspace = appStore.workspaces.find((ws) => ws.id === activeId)
  return activeWorkspace?.name || 'Choose a workspace'
})

async function selectWorkspace(id) {
  if (!id || id === appStore.activeWorkspaceId) {
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
    emit('select')
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
  } catch {
    // Ignore bootstrap failures here. The parent app handles global state recovery.
  }
})
</script>

<style scoped>
.workspace-dropdown-enter-active,
.workspace-dropdown-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.workspace-dropdown-enter-from,
.workspace-dropdown-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
