<template>
  <div
    class="relative z-40 flex h-full min-h-0 shrink-0 flex-col overflow-hidden"
    style="background-color: var(--color-sidebar-surface);"
  >
    <div
      class="sidebar-brand-shell h-14 shrink-0 border-b"
      style="border-color: var(--color-border);"
    >
      <button
        class="h-full w-full px-2 transition-colors duration-150"
        :class="appStore.isSidebarCollapsed ? 'justify-center' : 'justify-start'"
        style="color: var(--color-text-main);"
        :title="appStore.isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"
        @click="handleBrandClick"
      >
        <span class="flex h-full w-full items-center gap-2">
          <span class="flex h-8 w-8 shrink-0 items-center justify-center">
            <img :src="logo" alt="Inquira" class="h-8 w-8 rounded-lg shadow-sm" />
          </span>
          <span
            class="sidebar-brand-wordmark min-w-0 overflow-hidden whitespace-nowrap transition-[max-width,opacity] duration-200 ease-linear"
            :class="appStore.isSidebarCollapsed ? 'sidebar-brand-wordmark-collapsed' : 'sidebar-brand-wordmark-expanded'"
          >
            <span class="block text-[15px] font-bold leading-[1.3]" style="color: var(--color-text-main);">Inquira</span>
          </span>
        </span>
      </button>
    </div>

    <div class="flex min-h-0 flex-1 flex-col">
      <div v-show="!appStore.isSidebarCollapsed" class="flex min-h-0 flex-1 flex-col">
        <div class="border-b px-4 py-4" style="border-color: var(--color-border);">
          <p class="text-[11px] font-semibold uppercase tracking-[0.16em]" style="color: var(--color-text-muted);">Workspace</p>
          <button
            type="button"
            class="mt-3 flex w-full items-center gap-3 rounded-xl border px-3 py-3 text-left transition-colors hover:bg-[var(--color-panel-muted)]"
            style="border-color: var(--color-border); background-color: var(--color-panel-elevated);"
            title="Open workspace settings"
            @click="openSettings('workspace', 1)"
          >
            <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg" style="background-color: var(--color-selected-surface); color: var(--color-accent);">
              <FolderOpenIcon class="h-4 w-4" />
            </span>
            <span class="min-w-0 flex-1">
              <span class="block truncate text-[16px] font-semibold leading-[1.3]" style="color: var(--color-text-main);">
                {{ activeWorkspaceName }}
              </span>
              <span class="mt-0.5 block truncate text-[12px]" style="color: var(--color-text-muted);">
                {{ activeWorkspaceCaption }}
              </span>
            </span>
          </button>
        </div>

        <div class="flex min-h-0 flex-1 flex-col px-3 pb-3 pt-4">
          <div class="flex items-center justify-between px-1 pb-2">
            <p class="text-[11px] font-semibold uppercase tracking-[0.16em]" style="color: var(--color-text-muted);">Conversations</p>
            <button
              v-if="appStore.hasWorkspace"
              type="button"
              class="btn-icon h-7 w-7 shrink-0 rounded-lg"
              title="New Conversation"
              aria-label="New Conversation"
              @click.stop="createConversation"
            >
              <PlusIcon class="h-3.5 w-3.5" />
            </button>
          </div>

          <div class="custom-scrollbar flex-1 overflow-y-auto overflow-x-hidden">
            <div
              v-if="appStore.workspaceDeletionJobs.length > 0"
              class="mb-3 flex items-center gap-2 rounded-xl px-3 py-2 text-[11px]"
              style="background-color: var(--color-warning-bg); color: var(--color-warning-text);"
            >
              <svg class="h-3 w-3 shrink-0 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle class="opacity-30" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-90" d="M22 12a10 10 0 0 1-10 10" stroke="currentColor" stroke-width="4" />
              </svg>
              <span class="truncate">Deleting workspace...</span>
            </div>

            <div v-if="!appStore.hasWorkspace" class="px-3 py-3 text-sm" style="color: var(--color-text-muted);">
              Create a workspace to start a conversation.
            </div>

            <div v-else-if="filteredConversations.length === 0 && appStore.conversations.length > 0" class="px-3 py-3 text-sm" style="color: var(--color-text-muted);">
              No conversation matches found.
            </div>

            <div v-else-if="appStore.conversations.length === 0" class="px-3 py-3 text-sm" style="color: var(--color-text-muted);">
              No conversations yet.
            </div>

            <div v-else class="space-y-1">
              <div
                v-for="conv in filteredConversations"
                :key="conv.id"
                class="group sidebar-conversation-row"
                :class="{ 'sidebar-conversation-row-active': appStore.activeConversationId === conv.id }"
                @click="selectConversation(conv.id)"
              >
                <div class="flex min-w-0 flex-1 items-center pr-2" @dblclick="startEditing(conv)">
                  <div class="min-w-0 flex-1">
                    <div v-if="editingId === conv.id" class="relative z-10 flex w-full items-center gap-1">
                      <input
                        :ref="(el) => { if (el) editInputs[conv.id] = el }"
                        v-model="editingTitleValue"
                        class="input-base px-1 py-0.5 text-[13px] font-medium"
                        @keydown.enter.prevent="saveTitle(conv.id)"
                        @keydown.esc.prevent="cancelEditing"
                        @blur="saveTitle(conv.id)"
                        @click.stop
                      />
                    </div>
                    <template v-else>
                      <p
                        class="truncate text-[15px] leading-[1.35]"
                        :class="conv.id === appStore.activeConversationId ? 'font-semibold text-[var(--color-text-main)]' : 'font-medium text-[var(--color-text-main)]'"
                        :title="conv.title || 'Untitled'"
                      >
                        {{ conv.title || 'Untitled' }}
                      </p>
                    </template>
                  </div>
                </div>
                <div v-if="editingId !== conv.id" class="relative flex flex-shrink-0 items-center opacity-0 transition-opacity group-hover:opacity-100">
                  <button
                    type="button"
                    class="btn-icon rounded-lg p-1 hover:text-[var(--color-accent)]"
                    style="color: var(--color-text-muted);"
                    title="Conversation actions"
                    @click.stop="toggleConversationMenu(conv.id)"
                  >
                    <EllipsisHorizontalIcon class="h-3.5 w-3.5" />
                  </button>
                  <div
                    v-if="conversationMenuId === conv.id"
                    class="absolute right-0 top-7 z-20 w-32 overflow-hidden rounded-lg border shadow-lg"
                    style="border-color: var(--color-border-strong); background-color: var(--color-surface);"
                    data-conversation-actions-menu
                  >
                    <button
                      type="button"
                      class="w-full px-3 py-2 text-left text-xs font-medium transition-colors hover:bg-[var(--color-base-soft)]"
                      style="color: var(--color-text-main);"
                      @click.stop="startEditingFromMenu(conv)"
                    >
                      Rename
                    </button>
                    <button
                      type="button"
                      class="sidebar-menu-danger w-full px-3 py-2 text-left text-xs font-medium transition-colors"
                      style="color: var(--color-danger);"
                      @click.stop="confirmDeleteConversation(conv.id)"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <nav
        class="mt-auto border-t px-2 py-3"
        style="border-color: var(--color-border);"
      >
        <div class="flex flex-col gap-1">
          <button
            type="button"
            class="sidebar-rail-btn"
            :class="appStore.isSidebarCollapsed ? 'sidebar-rail-btn-collapsed' : 'sidebar-rail-btn-expanded'"
            title="Create Workspace"
            aria-label="Create Workspace"
            @click="openSettings('workspace', 1)"
          >
            <FolderPlusIcon class="h-4 w-4 shrink-0" />
            <span v-if="!appStore.isSidebarCollapsed" class="truncate text-sm font-medium">Create Workspace</span>
          </button>

          <button
            type="button"
            class="sidebar-rail-btn"
            :class="appStore.isSidebarCollapsed ? 'sidebar-rail-btn-collapsed' : 'sidebar-rail-btn-expanded'"
            title="LLM & API Keys"
            aria-label="LLM & API Keys"
            @click="openSettings('llm')"
          >
            <KeyIcon class="h-4 w-4 shrink-0" />
            <span v-if="!appStore.isSidebarCollapsed" class="truncate text-sm font-medium">LLM &amp; API Keys</span>
          </button>

          <div class="relative">
            <button
              ref="profileMenuButtonRef"
              type="button"
              class="sidebar-rail-btn"
              :class="[
                appStore.isSidebarCollapsed ? 'sidebar-rail-btn-collapsed' : 'sidebar-rail-btn-expanded',
                profileMenuOpen ? 'sidebar-rail-btn-active' : '',
              ]"
              title="User Profile"
              aria-label="User Profile"
              @click="toggleProfileMenu"
            >
              <span
                class="flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold uppercase"
                style="background-color: var(--color-selected-surface); color: var(--color-accent-text);"
              >
                {{ profileInitials }}
              </span>
              <span v-if="!appStore.isSidebarCollapsed" class="truncate text-sm font-medium">User Profile</span>
            </button>
          </div>
        </div>
      </nav>
    </div>

    <Teleport to="body">
      <div
        v-if="profileMenuOpen"
        ref="profileMenuRef"
        class="layer-modal-dropdown fixed overflow-hidden rounded-xl border shadow-lg"
        :style="profileMenuStyle"
        data-profile-menu
      >
        <button
          type="button"
          class="w-full px-3 py-2 text-left text-sm transition-colors hover:bg-[var(--color-base-soft)]"
          style="color: var(--color-text-main);"
          @click="openProfileSection('terms')"
        >
          Terms and Conditions
        </button>
        <button
          type="button"
          class="w-full px-3 py-2 text-left text-sm transition-colors hover:bg-[var(--color-base-soft)]"
          style="color: var(--color-text-main);"
          @click="openProfileSection('account')"
        >
          Account
        </button>
        <button
          type="button"
          class="w-full px-3 py-2 text-left text-sm transition-colors hover:bg-[var(--color-base-soft)]"
          style="color: var(--color-text-main);"
          @click="openProfileSection('appearance')"
        >
          Theme
        </button>
      </div>
    </Teleport>

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
import { ref, computed, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { useAppStore } from '../../stores/appStore'
import { useAuthStore } from '../../stores/authStore'
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
} from '@heroicons/vue/24/outline'

const appStore = useAppStore()
const authStore = useAuthStore()

const searchQuery = ref('')
const editingId = ref(null)
const editingTitleValue = ref('')
const editInputs = ref({})
const conversationMenuId = ref('')
const profileMenuOpen = ref(false)
const profileMenuRef = ref(null)
const profileMenuButtonRef = ref(null)
const profileMenuStyle = ref({
  left: '0px',
  top: '0px',
  minWidth: '13rem',
  transform: 'translateY(-100%)',
  backgroundColor: 'var(--color-panel-elevated)',
  borderColor: 'var(--color-border-strong)',
})

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
const profileInitials = computed(() => {
  const raw = String(authStore.username || 'User').trim()
  const parts = raw.split(/\s+/).filter(Boolean)
  const initials = parts.slice(0, 2).map((part) => part[0] || '').join('')
  return (initials || raw.slice(0, 2) || 'U').toUpperCase()
})

function workspaceFilename(duckdbPath) {
  const normalized = String(duckdbPath || '').trim()
  if (!normalized) return 'workspace.duckdb'
  return normalized.split('/').pop() || 'workspace.duckdb'
}

function handleBrandClick() {
  appStore.setSidebarCollapsed(!appStore.isSidebarCollapsed)
}

function updateProfileMenuPosition() {
  const button = profileMenuButtonRef.value
  if (!button || typeof button.getBoundingClientRect !== 'function') return
  const rect = button.getBoundingClientRect()
  profileMenuStyle.value = {
    left: `${rect.left}px`,
    top: `${Math.max(0, rect.top - 8)}px`,
    minWidth: `${Math.max(rect.width, 208)}px`,
    transform: 'translateY(-100%)',
    backgroundColor: 'var(--color-panel-elevated)',
    borderColor: 'var(--color-border-strong)',
  }
}

async function toggleProfileMenu() {
  profileMenuOpen.value = !profileMenuOpen.value
  if (!profileMenuOpen.value) return
  await nextTick()
  updateProfileMenuPosition()
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

function handleViewportChange() {
  if (!profileMenuOpen.value) return
  updateProfileMenuPosition()
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
  const fullPath = String(dataset?.file_path || '').trim()
  return fullPath
}

async function fetchDatasets() {
  const activeWorkspace = appStore.workspaces.find((ws) => ws.id === appStore.activeWorkspaceId)
  if (!activeWorkspace) {
    localDatasets.value = []
    return
  }
  isLoadingDatasets.value = true
  try {
    const response = await apiService.v1ListDatasets(activeWorkspace.id)
    const workspaceDatasets = response?.datasets || []
    localDatasets.value = workspaceDatasets
      .map((item) => ({
        table_name: item.table_name,
        file_path: item.source_path,
      }))
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
    if (appStore.activeConversationId) {
      await appStore.fetchConversationTurns({ reset: true })
    }
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

    window.dispatchEvent(new CustomEvent('dataset-switched', {
      detail: { tableName: selectedTableName, dataPath: selectedPath },
    }))
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

  if (!newTitle || newTitle === (conv?.title || 'Untitled')) {
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

function openSettings(tab = 'llm', step = 1) {
  const normalized = String(tab || '').trim().toLowerCase()
  if (normalized === 'api' || normalized === 'llm') {
    settingsInitialTab.value = 'llm'
  } else if (normalized === 'workspace' || normalized === 'data') {
    settingsInitialTab.value = 'workspace'
  } else if (normalized === 'account') {
    settingsInitialTab.value = 'account'
  } else if (normalized === 'appearance' || normalized === 'theme') {
    settingsInitialTab.value = 'appearance'
  } else if (normalized === 'terms' || normalized === 'legal') {
    settingsInitialTab.value = 'terms'
  } else {
    settingsInitialTab.value = 'llm'
  }
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
        const detail = String(job?.error_message || '').trim()
        toast.error('Dataset deletion failed', detail || `Background cleanup failed for "${displayName}".`)
        return
      }
      if (Date.now() - startedAt > timeoutMs) {
        datasetDeletionPollers.delete(normalizedJobId)
        return
      }
      const timer = setTimeout(poll, 2000)
      datasetDeletionPollers.set(normalizedJobId, timer)
    } catch (_error) {
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
          toast.info(
            'Dataset deletion started',
            deletedActiveDataset
              ? 'Dataset removed. Active selection cleared. Background cleanup started.'
              : 'Dataset removed from workspace. Background cleanup started.',
          )
          trackDatasetDeletionJob(workspaceId, jobId, datasetFriendlyName(deletedTableName))
        } else {
          toast.success(
            'Dataset Deleted',
            deletedActiveDataset ? 'Dataset removed. Active selection cleared.' : 'Dataset has been removed.',
          )
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
    // Ignore bootstrap failures here. The parent app handles global state recovery.
  }
  window.addEventListener('dataset-switched', handleDatasetCatalogChanged)
  window.addEventListener('sidebar-open-settings', handleOpenSettingsRequest)
  window.addEventListener('click', handleGlobalClick)
  window.addEventListener('resize', handleViewportChange)
  window.addEventListener('scroll', handleViewportChange, true)
})

onUnmounted(() => {
  window.removeEventListener('dataset-switched', handleDatasetCatalogChanged)
  window.removeEventListener('sidebar-open-settings', handleOpenSettingsRequest)
  window.removeEventListener('click', handleGlobalClick)
  window.removeEventListener('resize', handleViewportChange)
  window.removeEventListener('scroll', handleViewportChange, true)
  stopDatasetDeletionPollers()
})

watch(() => appStore.activeWorkspaceId, async (newId) => {
  if (newId) {
    await fetchDatasets()
    await appStore.fetchConversations()
  } else {
    localDatasets.value = []
  }
})

watch(() => appStore.isSidebarCollapsed, (collapsed) => {
  if (collapsed) {
    searchQuery.value = ''
    closeProfileMenu()
    closeConversationMenu()
  }
})

watch(() => authStore.username, () => {
  if (profileMenuOpen.value) {
    void nextTick().then(() => {
      updateProfileMenuPosition()
    })
  }
})
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
  height: 4px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: color-mix(in srgb, var(--color-border) 60%, transparent);
  border-radius: 4px;
}

.custom-scrollbar:hover::-webkit-scrollbar-thumb {
  background: color-mix(in srgb, var(--color-border) 80%, transparent);
}

.sidebar-brand-shell button {
  display: flex;
  align-items: center;
  border: 0;
  background: transparent;
}

.sidebar-brand-shell button:hover {
  background-color: color-mix(in srgb, var(--color-text-main) 4%, transparent);
}

.sidebar-brand-wordmark {
  overflow: hidden;
  text-align: left;
}

.sidebar-brand-wordmark-expanded {
  max-width: 160px;
  opacity: 1;
}

.sidebar-brand-wordmark-collapsed {
  max-width: 0;
  opacity: 0;
}

.sidebar-rail {
  display: flex;
  min-height: 0;
  flex-direction: column;
}

.sidebar-rail-collapsed {
  width: 48px;
}

.sidebar-rail-expanded {
  width: 160px;
}

.sidebar-rail-btn {
  border-radius: 0.75rem;
  border: 1px solid transparent;
  color: var(--color-text-muted);
  background: transparent;
  display: flex;
  align-items: center;
  transition: background-color 140ms ease, border-color 140ms ease, color 140ms ease;
}

.sidebar-rail-btn-collapsed {
  width: 32px;
  height: 32px;
  justify-content: center;
}

.sidebar-rail-btn-expanded {
  width: 100%;
  min-height: 36px;
  gap: 0.75rem;
  padding: 0.5rem 0.75rem;
  justify-content: flex-start;
}

.sidebar-rail-btn:hover {
  background-color: color-mix(in srgb, var(--color-text-main) 6%, transparent);
  border-color: var(--color-border);
  color: var(--color-text-main);
}

.sidebar-rail-btn-active {
  color: var(--color-accent);
  border-color: color-mix(in srgb, var(--color-accent) 35%, var(--color-border));
  background-color: color-mix(in srgb, var(--color-accent) 14%, transparent);
}

.sidebar-item-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.3rem 0.5rem;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: background-color 150ms ease, color 150ms ease;
  line-height: 1.4;
}

.sidebar-item-row:hover {
  background-color: color-mix(in srgb, var(--color-accent) 8%, transparent);
}

.sidebar-item-row-active {
  background-color: var(--color-chat-user-bubble);
}

.sidebar-conversation-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-height: 3.5rem;
  padding: 0.75rem 0.875rem;
  border-radius: 1rem;
  cursor: pointer;
  transition: background-color 150ms ease, color 150ms ease;
}

.sidebar-conversation-row:hover {
  background-color: var(--color-panel-muted);
}

.sidebar-conversation-row-active {
  background-color: var(--color-selected-surface);
  box-shadow: inset 0 0 0 1px var(--color-selected-border);
}

.sidebar-menu-danger:hover {
  background-color: var(--color-danger-bg);
}
</style>
