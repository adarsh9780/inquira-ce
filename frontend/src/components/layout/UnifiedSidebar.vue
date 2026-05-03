<template>
  <div
    class="relative z-40 flex h-full min-h-0 shrink-0 flex-col overflow-hidden sidebar-root"
    style="background-color: var(--color-sidebar-surface);"
  >
    <!-- Brand / Collapse Toggle -->
    <div class="sidebar-brand-shell h-14 shrink-0">
      <button
        class="brand-btn h-full w-full px-3"
        :class="appStore.isSidebarCollapsed ? 'justify-center' : 'justify-start'"
        :title="appStore.isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"
        @click="handleBrandClick"
      >
        <span class="flex h-full w-full items-center gap-2.5">
          <span class="flex h-7 w-7 shrink-0 items-center justify-center">
            <img :src="logo" alt="Inquira" class="h-7 w-7 rounded-md" />
          </span>
          <span
            class="sidebar-brand-wordmark"
            :class="appStore.isSidebarCollapsed ? 'sidebar-brand-wordmark-collapsed' : 'sidebar-brand-wordmark-expanded'"
          >
            <span class="block text-[14px] font-semibold tracking-tight leading-none" style="color: var(--color-text-main);">Inquira</span>
          </span>
        </span>
      </button>
    </div>

    <div class="flex min-h-0 flex-1 flex-col">
      <div v-show="!appStore.isSidebarCollapsed" class="flex min-h-0 flex-1 flex-col">

        <!-- Active Workspace -->
        <div class="px-3 pt-3 pb-2">
          <button
            type="button"
            class="workspace-btn w-full flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-left"
            title="Open workspace settings"
            @click="openSettings('workspace', 1)"
          >
            <span class="workspace-icon flex h-6 w-6 shrink-0 items-center justify-center rounded-md">
              <FolderOpenIcon class="h-3.5 w-3.5" />
            </span>
            <span class="min-w-0 flex-1">
              <span class="block truncate text-[13px] font-semibold leading-snug" style="color: var(--color-text-main);">
                {{ activeWorkspaceName }}
              </span>
              <span class="block truncate text-[11px] leading-snug" style="color: var(--color-text-muted);">
                {{ activeWorkspaceCaption }}
              </span>
            </span>
          </button>
        </div>

        <div class="sidebar-divider mx-3" />

        <!-- Conversations -->
        <div class="flex min-h-0 flex-1 flex-col px-2 pb-2 pt-2">
          <div class="flex items-center justify-between px-1.5 pb-1.5">
            <span class="text-[10px] font-semibold uppercase tracking-widest" style="color: var(--color-text-muted); opacity: 0.6;">Chats</span>
            <button
              v-if="appStore.hasWorkspace"
              type="button"
              class="new-conv-btn flex h-5 w-5 items-center justify-center rounded-md"
              title="New Conversation"
              aria-label="New Conversation"
              @click.stop="createConversation"
            >
              <PlusIcon class="h-3 w-3" />
            </button>
          </div>

          <!-- Workspace deletion banner -->
          <div
            v-if="appStore.workspaceDeletionJobs.length > 0"
            class="deletion-banner mb-2 flex items-center gap-2 rounded-md px-2.5 py-1.5 text-[11px]"
          >
            <svg class="h-2.5 w-2.5 shrink-0 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle class="opacity-30" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
              <path class="opacity-90" d="M22 12a10 10 0 0 1-10 10" stroke="currentColor" stroke-width="4" />
            </svg>
            <span class="truncate">Deleting workspace…</span>
          </div>

          <div class="custom-scrollbar flex-1 overflow-y-auto overflow-x-hidden">
            <div v-if="!appStore.hasWorkspace" class="px-2 py-2 text-[12px]" style="color: var(--color-text-muted);">
              Create a workspace to start.
            </div>
            <div v-else-if="filteredConversations.length === 0 && appStore.conversations.length > 0" class="px-2 py-2 text-[12px]" style="color: var(--color-text-muted);">
              No matches found.
            </div>
            <div v-else-if="appStore.conversations.length === 0" class="px-2 py-2 text-[12px]" style="color: var(--color-text-muted);">
              No conversations yet.
            </div>

            <div v-else class="space-y-0.5">
              <div
                v-for="conv in filteredConversations"
                :key="conv.id"
                class="group conv-row"
                :class="{ 'conv-row-active': appStore.activeConversationId === conv.id }"
                @click="selectConversation(conv.id)"
              >
                <!-- Inline edit mode -->
                <div v-if="editingId === conv.id" class="flex w-full items-center gap-1 px-0.5" @click.stop>
                  <input
                    :ref="(el) => { if (el) editInputs[conv.id] = el }"
                    v-model="editingTitleValue"
                    class="conv-edit-input flex-1 px-1.5 py-0.5 text-[13px]"
                    @keydown.enter.prevent="saveTitle(conv.id)"
                    @keydown.esc.prevent="cancelEditing"
                    @blur="saveTitle(conv.id)"
                  />
                </div>

                <!-- Display mode -->
                <template v-else>
                  <p
                    class="min-w-0 flex-1 truncate text-[13px] leading-snug"
                    :class="conv.id === appStore.activeConversationId
                      ? 'font-medium conv-title-active'
                      : 'conv-title-idle'"
                    :title="conv.title || 'Untitled'"
                    @dblclick="startEditing(conv)"
                  >
                    {{ conv.title || 'Untitled' }}
                  </p>

                  <div class="relative flex shrink-0 items-center opacity-0 transition-opacity group-hover:opacity-100">
                    <button
                      type="button"
                      class="conv-action-btn rounded-md p-0.5"
                      title="Conversation actions"
                      @click.stop="toggleConversationMenu(conv.id)"
                    >
                      <EllipsisHorizontalIcon class="h-3.5 w-3.5" />
                    </button>

                    <div
                      v-if="conversationMenuId === conv.id"
                      class="conv-menu absolute right-0 top-6 z-20 w-28 overflow-hidden rounded-lg border shadow-md"
                      data-conversation-actions-menu
                    >
                      <button
                        type="button"
                        class="conv-menu-item w-full px-3 py-1.5 text-left text-[12px] font-medium"
                        @click.stop="startEditingFromMenu(conv)"
                      >
                        Rename
                      </button>
                      <button
                        type="button"
                        class="conv-menu-item conv-menu-danger w-full px-3 py-1.5 text-left text-[12px] font-medium"
                        @click.stop="confirmDeleteConversation(conv.id)"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </template>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Bottom Nav -->
      <nav class="mt-auto px-2 pb-3 pt-2">
        <div class="sidebar-divider mb-3" />
        <div class="flex flex-col gap-0.5">
          <button
            type="button"
            class="nav-btn"
            :class="appStore.isSidebarCollapsed ? 'nav-btn-collapsed' : 'nav-btn-expanded'"
            title="Create Workspace"
            aria-label="Create Workspace"
            @click="openSettings('workspace', 1)"
          >
            <FolderPlusIcon class="h-4 w-4 shrink-0" />
            <span v-if="!appStore.isSidebarCollapsed" class="truncate text-[13px] font-medium">New Workspace</span>
          </button>

          <div class="sidebar-divider my-1" />

          <button
            type="button"
            class="nav-btn"
            :class="appStore.isSidebarCollapsed ? 'nav-btn-collapsed' : 'nav-btn-expanded'"
            title="LLM & API Keys"
            aria-label="LLM & API Keys"
            @click="openSettings('llm')"
          >
            <KeyIcon class="h-4 w-4 shrink-0" />
            <span v-if="!appStore.isSidebarCollapsed" class="truncate text-[13px] font-medium">API Keys</span>
          </button>

          <div class="relative">
            <button
              ref="profileMenuButtonRef"
              type="button"
              class="nav-btn"
              :class="[
                appStore.isSidebarCollapsed ? 'nav-btn-collapsed' : 'nav-btn-expanded',
                profileMenuOpen ? 'nav-btn-active' : '',
              ]"
              title="User Profile"
              aria-label="User Profile"
              @click="toggleProfileMenu"
            >
              <UserCircleIcon class="h-4 w-4 shrink-0" />
              <span v-if="!appStore.isSidebarCollapsed" class="truncate text-[13px] font-medium">Profile</span>
            </button>

            <div
              v-if="profileMenuOpen"
              ref="profileMenuRef"
              class="profile-menu absolute bottom-0 left-full z-[var(--z-dropdown)] ml-2 w-48 overflow-hidden rounded-xl border shadow-lg"
              data-profile-menu
            >
              <button type="button" class="profile-menu-item w-full px-3 py-2 text-left text-[13px]" @click="openProfileSection('terms')">Terms &amp; Conditions</button>
              <button type="button" class="profile-menu-item w-full px-3 py-2 text-left text-[13px]" @click="openProfileSection('account')">Account</button>
              <button type="button" class="profile-menu-item w-full px-3 py-2 text-left text-[13px]" @click="openProfileSection('appearance')">Theme</button>
            </div>
          </div>
        </div>
      </nav>
    </div>

    <SettingsModal
      v-model="isSettingsOpen"
      :initial-tab="settingsInitialTab"
      :initial-step="settingsInitialStep"
    />

    <ConfirmationModal
      :is-open="isDeleteDialogOpen"
      :title="deleteDialogTitle"
      :message="deleteDialogMessage"
      confirm-text="Delete"
      cancel-text="Cancel"
      @close="closeDeleteDialog"
      @confirm="confirmDelete"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useAppStore } from '../../stores/appStore'
import { toast } from '../../composables/useToast'
import { extractApiErrorMessage } from '../../utils/apiError'
import { inferTableNameFromDataPath } from '../../utils/chatBootstrap'
import { previewService } from '../../services/previewService'
import SettingsModal from '../modals/SettingsModal.vue'
import ConfirmationModal from '../modals/ConfirmationModal.vue'
import logo from '../../assets/favicon.svg'
import apiService from '../../services/apiService'

import {
  FolderOpenIcon,
  FolderPlusIcon,
  PlusIcon,
  EllipsisHorizontalIcon,
  KeyIcon,
  UserCircleIcon,
} from '@heroicons/vue/24/outline'

const appStore = useAppStore()

const searchQuery = ref('')
const editingId = ref(null)
const editingTitleValue = ref('')
const editInputs = ref({})
const conversationMenuId = ref('')
const profileMenuOpen = ref(false)
const profileMenuRef = ref(null)
const profileMenuButtonRef = ref(null)

const workspacesExpanded = ref(true)
const datasetsExpanded = ref(true)
const conversationsExpanded = ref(true)

const localDatasets = ref([])
const isLoadingDatasets = ref(false)

const isSettingsOpen = ref(false)
const settingsInitialTab = ref('llm')
const settingsInitialStep = ref(1)

const isDeleteDialogOpen = ref(false)
const deleteDialogTitle = ref('')
const deleteDialogMessage = ref('')
const pendingDeleteType = ref('')
const pendingDeleteId = ref('')
const datasetDeletionPollers = new Map()

const filteredWorkspaces = computed(() => {
  const items = Array.isArray(appStore.workspaces) ? appStore.workspaces : []
  const query = String(searchQuery.value || '').trim().toLowerCase()
  if (!query) return items
  return items.filter((workspace) => {
    const name = String(workspace?.name || '').toLowerCase()
    const filename = workspaceFilename(workspace?.duckdb_path).toLowerCase()
    return name.includes(query) || filename.includes(query)
  })
})

const activeWorkspaceName = computed(() => {
  const activeId = String(appStore.activeWorkspaceId || '').trim()
  if (!activeId) return 'No active workspace'
  const activeWorkspace = appStore.workspaces.find((workspace) => workspace.id === activeId)
  return String(activeWorkspace?.name || '').trim() || 'Untitled workspace'
})

const activeWorkspaceCaption = computed(() => {
  if (!appStore.hasWorkspace) return 'Create a workspace to begin'
  const activeId = String(appStore.activeWorkspaceId || '').trim()
  const activeWorkspace = appStore.workspaces.find((workspace) => workspace.id === activeId)
  return workspaceFilename(activeWorkspace?.duckdb_path)
})

const filteredDatasets = computed(() => {
  if (!searchQuery.value) return localDatasets.value
  const query = searchQuery.value.toLowerCase()
  return localDatasets.value.filter((ds) => {
    const rawName = String(ds?.table_name || '').toLowerCase()
    const friendlyName = datasetFriendlyName(ds?.table_name).toLowerCase()
    const sourceName = datasetSourceCaption(ds?.file_path).toLowerCase()
    return rawName.includes(query) || friendlyName.includes(query) || sourceName.includes(query)
  })
})

const filteredConversations = computed(() => {
  if (!searchQuery.value) return appStore.conversations
  const query = searchQuery.value.toLowerCase()
  return appStore.conversations.filter((conv) => String(conv?.title || '').toLowerCase().includes(query))
})

function workspaceFilename(duckdbPath) {
  const normalized = String(duckdbPath || '').trim()
  if (!normalized) return 'workspace.duckdb'
  return normalized.split('/').pop() || 'workspace.duckdb'
}

function handleBrandClick() {
  appStore.setSidebarCollapsed(!appStore.isSidebarCollapsed)
}

function toggleProfileMenu() {
  profileMenuOpen.value = !profileMenuOpen.value
}

function closeProfileMenu() {
  profileMenuOpen.value = false
}

function openProfileSection(tab) {
  closeProfileMenu()
  openSettings(tab)
}

function handleOpenSettingsRequest(event) {
  const requestedTab = String(event?.detail?.tab || 'api').trim() || 'api'
  const requestedStep = Number(event?.detail?.step || 1)
  openSettings(requestedTab, requestedStep)
}

function handleGlobalClick(event) {
  const target = event?.target
  if (!(target instanceof Element)) return
  if (target.closest('[data-conversation-actions-menu]')) return
  if (profileMenuRef.value?.contains(target) || profileMenuButtonRef.value?.contains(target)) return
  closeConversationMenu()
  closeProfileMenu()
}

function datasetFriendlyName(tableName) {
  const raw = String(tableName || '').trim()
  if (!raw) return 'Untitled dataset'
  const hashSegmentIndex = raw.search(/_[0-9a-f]{6,}(?=_|$)/i)
  const withoutHashSuffix = hashSegmentIndex >= 0 ? raw.slice(0, hashSegmentIndex) : raw
  const compacted = withoutHashSuffix.replace(/_{2,}/g, '_').replace(/^_+|_+$/g, '')
  if (compacted) return compacted
  const firstToken = raw.split('_')[0]?.trim()
  return firstToken || 'Untitled dataset'
}

function datasetSourceCaption(filePath) {
  const normalized = String(filePath || '').trim().replace(/\\/g, '/')
  if (!normalized) return ''
  const parts = normalized.split('/').filter(Boolean)
  return parts[parts.length - 1] || normalized
}

function normalizeDatasetPath(path) {
  return String(path || '')
    .trim()
    .replace(/\\/g, '/')
    .replace(/\/{2,}/g, '/')
    .toLowerCase()
}

function isSelectedDataset(dataset) {
  const datasetPath = normalizeDatasetPath(dataset?.file_path)
  const activePath = normalizeDatasetPath(appStore.dataFilePath)
  if (datasetPath && activePath && datasetPath === activePath) return true
  const datasetTable = String(dataset?.table_name || '').trim().toLowerCase()
  const activeTable = String(appStore.ingestedTableName || '').trim().toLowerCase()
  return Boolean(datasetTable && activeTable && datasetTable === activeTable)
}

function datasetRowTitle(dataset) {
  return String(dataset?.file_path || '').trim()
}

async function fetchDatasets() {
  const activeWorkspace = appStore.workspaces.find((ws) => ws.id === appStore.activeWorkspaceId)
  if (!activeWorkspace) { localDatasets.value = []; return }
  isLoadingDatasets.value = true
  try {
    const response = await apiService.v1ListDatasets(activeWorkspace.id)
    const workspaceDatasets = response?.datasets || []
    localDatasets.value = workspaceDatasets
      .map((item) => ({ table_name: item.table_name, file_path: item.source_path }))
      .filter((item) => Boolean(String(item.table_name || '').trim()))
  } catch (error) {
    console.error('Failed to load datasets:', error)
    localDatasets.value = []
  } finally {
    isLoadingDatasets.value = false
  }
}

function handleDatasetCatalogChanged() {
  if (!appStore.hasWorkspace || !appStore.activeWorkspaceId) return
  void fetchDatasets()
}

async function selectWorkspace(id) {
  if (!id || id === appStore.activeWorkspaceId) return
  try {
    await appStore.activateWorkspace(id)
    await appStore.fetchConversations()
    if (appStore.activeConversationId) await appStore.fetchConversationTurns({ reset: true })
  } catch (error) {
    toast.error('Workspace Error', error.message || 'Failed to activate workspace')
  }
}

async function selectDataset(ds) {
  if (!ds || !ds.table_name) return
  try {
    let selectedPath = ds.file_path
    let selectedTableName = String(ds.table_name || inferTableNameFromDataPath(ds.file_path || '')).trim()
    if (appStore.activeWorkspaceId && ds.file_path && !String(ds.file_path).startsWith('browser://')) {
      const syncedDataset = await apiService.v1AddDataset(appStore.activeWorkspaceId, ds.file_path)
      selectedPath = syncedDataset?.source_path || selectedPath
      selectedTableName = String(syncedDataset?.table_name || selectedTableName).trim()
    }
    previewService.clearSchemaCache()
    appStore.setDataFilePath(selectedPath || '')
    appStore.setIngestedTableName(selectedTableName)
    appStore.setIngestedColumns([])
    appStore.setSchemaFileId(selectedPath || selectedTableName)
    appStore.setGeneratedCode('')
    appStore.setPythonFileContent('')
    appStore.setResultData(null)
    appStore.setPlotlyFigure(null)
    appStore.setDataframes([])
    appStore.setFigures([])
    appStore.setTerminalOutput('')
    window.dispatchEvent(new CustomEvent('dataset-switched', { detail: { tableName: selectedTableName, dataPath: selectedPath } }))
  } catch (error) {
    console.error('Failed to switch dataset:', error)
  }
}

async function createConversation() {
  try {
    const conversation = await appStore.createConversation()
    if (conversation?.id) {
      appStore.setActiveConversationId(conversation.id)
      await appStore.fetchConversationTurns({ reset: true })
    }
  } catch (error) {
    toast.error('Conversation Error', extractApiErrorMessage(error, 'Failed to create conversation'))
  }
}

async function selectConversation(id) {
  conversationMenuId.value = ''
  const targetConversationId = String(id || '').trim()
  if (!targetConversationId || targetConversationId === String(appStore.activeConversationId || '').trim()) return
  try {
    appStore.setActiveConversationId(targetConversationId)
    await appStore.fetchConversationTurns({ reset: true })
  } catch (error) {
    toast.error('Conversation Error', extractApiErrorMessage(error, 'Failed to load conversation'))
  }
}

function startEditing(conv) {
  conversationMenuId.value = ''
  editingId.value = conv.id
  editingTitleValue.value = conv.title || 'Untitled'
  setTimeout(() => {
    const inputEl = editInputs.value[conv.id]
    if (inputEl) { inputEl.focus(); inputEl.select() }
  }, 50)
}

function cancelEditing() {
  editingId.value = null
  editingTitleValue.value = ''
}

function toggleConversationMenu(conversationId) {
  const targetConversationId = String(conversationId || '').trim()
  if (!targetConversationId) return
  conversationMenuId.value = conversationMenuId.value === targetConversationId ? '' : targetConversationId
}

function startEditingFromMenu(conv) {
  conversationMenuId.value = ''
  startEditing(conv)
}

function closeConversationMenu() {
  conversationMenuId.value = ''
}

async function saveTitle(id) {
  if (editingId.value !== id) return
  const newTitle = editingTitleValue.value.trim()
  const conv = appStore.conversations.find((c) => c.id === id)
  if (!newTitle || newTitle === (conv?.title || 'Untitled')) { cancelEditing(); return }
  try {
    if (id === appStore.activeConversationId) {
      await appStore.updateConversationTitle(newTitle)
    } else {
      const updated = await apiService.v1UpdateConversation(id, newTitle)
      const idx = appStore.conversations.findIndex((c) => c.id === id)
      if (idx !== -1) appStore.conversations[idx] = { ...appStore.conversations[idx], title: updated.title }
    }
    toast.success('Renamed', 'Conversation title updated')
  } catch (error) {
    toast.error('Rename Failed', extractApiErrorMessage(error, 'Failed to update title'))
  } finally {
    cancelEditing()
  }
}

function openSettings(tab = 'llm', step = 1) {
  const normalized = String(tab || '').trim().toLowerCase()
  if (normalized === 'api' || normalized === 'llm') settingsInitialTab.value = 'llm'
  else if (normalized === 'workspace' || normalized === 'data') settingsInitialTab.value = 'workspace'
  else if (normalized === 'account') settingsInitialTab.value = 'account'
  else if (normalized === 'appearance' || normalized === 'theme') settingsInitialTab.value = 'appearance'
  else if (normalized === 'terms' || normalized === 'legal') settingsInitialTab.value = 'terms'
  else settingsInitialTab.value = 'llm'
  const parsedStep = Number(step)
  settingsInitialStep.value = Number.isFinite(parsedStep) && parsedStep >= 1 ? Math.floor(parsedStep) : 1
  isSettingsOpen.value = true
}

function confirmDeleteWorkspace(workspaceId) {
  const target = appStore.workspaces.find((ws) => ws.id === workspaceId)
  pendingDeleteType.value = 'workspace'
  pendingDeleteId.value = workspaceId
  deleteDialogTitle.value = 'Delete Workspace'
  deleteDialogMessage.value = `Are you sure you want to delete "${target?.name || 'this workspace'}"? Cleanup will run in the background and cannot be undone.`
  isDeleteDialogOpen.value = true
}

function confirmDeleteDataset(tableName) {
  const target = localDatasets.value.find((ds) => ds.table_name === tableName)
  pendingDeleteType.value = 'dataset'
  pendingDeleteId.value = tableName
  deleteDialogTitle.value = 'Delete Dataset'
  deleteDialogMessage.value = `Are you sure you want to delete "${target?.table_name || 'this dataset'}"? This action cannot be undone.`
  isDeleteDialogOpen.value = true
}

function confirmDeleteConversation(conversationId) {
  const target = appStore.conversations.find((c) => c.id === conversationId)
  closeConversationMenu()
  pendingDeleteType.value = 'conversation'
  pendingDeleteId.value = conversationId
  deleteDialogTitle.value = 'Delete Conversation'
  deleteDialogMessage.value = `Are you sure you want to delete "${target?.title || 'Untitled'}"? This action cannot be undone.`
  isDeleteDialogOpen.value = true
}

function closeDeleteDialog() {
  isDeleteDialogOpen.value = false
  pendingDeleteType.value = ''
  pendingDeleteId.value = ''
  deleteDialogTitle.value = ''
  deleteDialogMessage.value = ''
}

function stopDatasetDeletionPollers() {
  datasetDeletionPollers.forEach((timerId) => clearTimeout(timerId))
  datasetDeletionPollers.clear()
}

function trackDatasetDeletionJob(workspaceId, jobId, datasetLabel, timeoutMs = 300000) {
  const normalizedWorkspaceId = String(workspaceId || '').trim()
  const normalizedJobId = String(jobId || '').trim()
  if (!normalizedWorkspaceId || !normalizedJobId) return
  if (datasetDeletionPollers.has(normalizedJobId)) return
  const startedAt = Date.now()
  const displayName = String(datasetLabel || '').trim() || 'dataset'

  const poll = async () => {
    try {
      const job = await apiService.v1GetDatasetDeletionJob(normalizedWorkspaceId, normalizedJobId)
      const status = String(job?.status || '').trim().toLowerCase()
      if (status === 'completed') {
        datasetDeletionPollers.delete(normalizedJobId)
        toast.success('Dataset deletion completed', `"${displayName}" cleanup finished.`)
        return
      }
      if (status === 'failed') {
        datasetDeletionPollers.delete(normalizedJobId)
        toast.error('Dataset deletion failed', String(job?.error_message || '').trim() || `Background cleanup failed for "${displayName}".`)
        return
      }
      if (Date.now() - startedAt > timeoutMs) { datasetDeletionPollers.delete(normalizedJobId); return }
      const timer = setTimeout(poll, 2000)
      datasetDeletionPollers.set(normalizedJobId, timer)
    } catch {
      datasetDeletionPollers.delete(normalizedJobId)
    }
  }

  poll()
}

async function confirmDelete() {
  if (!pendingDeleteId.value) return
  try {
    if (pendingDeleteType.value === 'workspace') {
      const job = await appStore.deleteWorkspaceAsync(pendingDeleteId.value)
      toast.info('Workspace Deletion Started', `Deleting workspace in background (job: ${job.job_id.slice(0, 8)}...).`)
    } else if (pendingDeleteType.value === 'dataset') {
      const workspaceId = appStore.activeWorkspaceId
      if (workspaceId) {
        const deletedTableName = String(pendingDeleteId.value || '').trim()
        const job = await apiService.v1DeleteDataset(workspaceId, deletedTableName)
        const deletedActiveDataset = appStore.handleDatasetRemoved(deletedTableName)
        previewService.clearSchemaCache()
        window.dispatchEvent(new CustomEvent('dataset-switched', { detail: null }))
        await fetchDatasets()
        const jobId = String(job?.job_id || '').trim()
        if (jobId) {
          toast.info('Dataset deletion started', deletedActiveDataset ? 'Dataset removed. Active selection cleared. Background cleanup started.' : 'Dataset removed from workspace. Background cleanup started.')
          trackDatasetDeletionJob(workspaceId, jobId, datasetFriendlyName(deletedTableName))
        } else {
          toast.success('Dataset Deleted', deletedActiveDataset ? 'Dataset removed. Active selection cleared.' : 'Dataset has been removed.')
        }
      }
    } else if (pendingDeleteType.value === 'conversation') {
      await appStore.deleteConversationById(pendingDeleteId.value)
      toast.success('Conversation Deleted', 'Conversation has been removed.')
    }
    closeDeleteDialog()
  } catch (error) {
    toast.error('Delete Error', extractApiErrorMessage(error, 'Failed to delete'))
  }
}

onMounted(async () => {
  try {
    await appStore.fetchWorkspaces()
    await appStore.fetchWorkspaceDeletionJobs()
    if (appStore.activeWorkspaceId) {
      await fetchDatasets()
      await appStore.fetchConversations()
    }
  } catch {
    // Ignore bootstrap failures - parent app handles global state recovery.
  }
  window.addEventListener('dataset-switched', handleDatasetCatalogChanged)
  window.addEventListener('sidebar-open-settings', handleOpenSettingsRequest)
  window.addEventListener('click', handleGlobalClick)
})

onUnmounted(() => {
  window.removeEventListener('dataset-switched', handleDatasetCatalogChanged)
  window.removeEventListener('sidebar-open-settings', handleOpenSettingsRequest)
  window.removeEventListener('click', handleGlobalClick)
  stopDatasetDeletionPollers()
})

watch(() => appStore.activeWorkspaceId, async (newId) => {
  if (newId) { await fetchDatasets(); await appStore.fetchConversations() }
  else localDatasets.value = []
})

watch(() => appStore.isSidebarCollapsed, (collapsed) => {
  if (collapsed) { searchQuery.value = ''; closeProfileMenu(); closeConversationMenu() }
})
</script>

<style scoped>
/* -- Scrollbar -- */
.custom-scrollbar::-webkit-scrollbar { width: 3px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: color-mix(in srgb, var(--color-border) 50%, transparent);
  border-radius: 4px;
}
.custom-scrollbar:hover::-webkit-scrollbar-thumb {
  background: color-mix(in srgb, var(--color-border) 75%, transparent);
}

/* -- Divider -- */
.sidebar-divider {
  height: 1px;
  background: var(--color-border);
  opacity: 0.5;
}

/* -- Brand -- */
.brand-btn {
  display: flex;
  align-items: center;
  border: none;
  background: transparent;
  cursor: pointer;
  border-radius: 0;
  transition: background-color 120ms ease;
}
.brand-btn:hover {
  background-color: color-mix(in srgb, var(--color-text-main) 4%, transparent);
}
.sidebar-brand-wordmark {
  overflow: hidden;
  text-align: left;
  transition: max-width 200ms ease, opacity 200ms ease;
}
.sidebar-brand-wordmark-expanded { max-width: 160px; opacity: 1; }
.sidebar-brand-wordmark-collapsed { max-width: 0; opacity: 0; }

/* -- Workspace button -- */
.workspace-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  transition: background-color 120ms ease;
  border-radius: 8px;
}
.workspace-btn:hover {
  background-color: color-mix(in srgb, var(--color-text-main) 5%, transparent);
}
.workspace-icon {
  color: var(--color-accent);
  background-color: color-mix(in srgb, var(--color-accent) 12%, transparent);
}

/* -- New conversation button -- */
.new-conv-btn {
  border: none;
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  transition: background-color 120ms ease, color 120ms ease;
}
.new-conv-btn:hover {
  background-color: color-mix(in srgb, var(--color-text-main) 6%, transparent);
  color: var(--color-text-main);
}

/* -- Conversation rows -- */
.conv-row {
  display: flex;
  align-items: center;
  gap: 4px;
  min-height: 32px;
  padding: 5px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 120ms ease;
}
.conv-row:hover { background-color: color-mix(in srgb, var(--color-text-main) 5%, transparent); }
.conv-row-active { background-color: var(--color-selected-surface); }

.conv-title-idle { color: var(--color-text-muted); }
.conv-title-active { color: var(--color-text-main); }

/* -- Conversation action button -- */
.conv-action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  transition: background-color 120ms ease, color 120ms ease;
}
.conv-action-btn:hover {
  background-color: color-mix(in srgb, var(--color-text-main) 8%, transparent);
  color: var(--color-text-main);
}

/* -- Conversation context menu -- */
.conv-menu {
  border-color: var(--color-border);
  background-color: var(--color-surface);
}
.conv-menu-item {
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--color-text-main);
  transition: background-color 100ms ease;
}
.conv-menu-item:hover { background-color: var(--color-panel-muted); }
.conv-menu-danger { color: var(--color-danger) !important; }
.conv-menu-danger:hover { background-color: var(--color-danger-bg) !important; }

/* -- Inline edit input -- */
.conv-edit-input {
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background-color: var(--color-surface);
  color: var(--color-text-main);
  outline: none;
  width: 100%;
  font-size: 13px;
  transition: border-color 120ms ease;
}
.conv-edit-input:focus { border-color: var(--color-accent); }

/* -- Bottom nav buttons -- */
.nav-btn {
  border-radius: 8px;
  border: none;
  color: var(--color-text-muted);
  background: transparent;
  display: flex;
  align-items: center;
  cursor: pointer;
  transition: background-color 120ms ease, color 120ms ease;
}
.nav-btn-collapsed { width: 32px; height: 32px; justify-content: center; }
.nav-btn-expanded { width: 100%; min-height: 32px; gap: 10px; padding: 6px 10px; justify-content: flex-start; }
.nav-btn:hover {
  background-color: color-mix(in srgb, var(--color-text-main) 6%, transparent);
  color: var(--color-text-main);
}
.nav-btn-active {
  color: var(--color-accent);
  background-color: color-mix(in srgb, var(--color-accent) 10%, transparent);
}

/* -- Profile menu -- */
.profile-menu {
  border-color: var(--color-border);
  background-color: var(--color-panel-elevated);
}
.profile-menu-item {
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--color-text-main);
  transition: background-color 100ms ease;
}
.profile-menu-item:hover { background-color: var(--color-panel-muted); }

/* -- Deletion banner -- */
.deletion-banner {
  background-color: var(--color-warning-bg);
  color: var(--color-warning-text);
}
</style>
