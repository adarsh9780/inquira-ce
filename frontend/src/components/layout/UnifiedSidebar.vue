<template>
  <div
    class="relative z-40 flex h-full min-h-0 shrink-0 flex-col overflow-hidden border-r border-[var(--color-border)] sidebar-root transition-[width] duration-300 ease-in-out"
    :class="appStore.isSidebarCollapsed ? 'w-[64px]' : 'w-[260px]'"
    style="background-color: var(--color-sidebar-surface);"
  >
    <!-- Brand / Collapse Toggle -->
    <!-- 20px explicit left padding + 24px icon = perfect 64px center -->
    <div class="h-14 shrink-0 border-b border-[var(--color-border)] flex items-center pl-[20px] pr-4">
      <button
        class="flex h-full w-full items-center transition-opacity hover:opacity-70 focus:outline-none"
        :title="appStore.isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"
        @click="handleBrandClick"
      >
        <div class="flex h-6 w-6 shrink-0 items-center justify-center">
          <img :src="logo" alt="Inquira" class="h-full w-full rounded-md" />
        </div>
        
        <div
          class="flex items-center overflow-hidden whitespace-nowrap transition-all duration-300 ease-in-out"
          :class="appStore.isSidebarCollapsed ? 'max-w-0 opacity-0 ml-0' : 'max-w-[200px] opacity-100 ml-3'"
        >
          <span class="text-[14px] font-semibold tracking-tight text-[var(--color-text-main)]">
            Inquira
          </span>
        </div>
      </button>
    </div>

    <!-- Main Navigation Content -->
    <!-- Global px-2 wrapper enforces the 8px outer margin for all pills -->
    <div class="flex min-h-0 flex-1 flex-col overflow-x-hidden px-2 custom-scrollbar">
      
      <!-- Active Workspace Section -->
      <div class="pt-3 pb-2">
        <!-- px-3 (12px) + outer px-2 (8px) = 20px perfect center offset -->
        <button
          type="button"
          class="flex w-full items-center rounded-lg px-3 py-2 text-left transition-colors hover:bg-[var(--color-text-main)]/5 focus:outline-none"
          :title="appStore.isSidebarCollapsed ? activeWorkspaceName : ''"
          @click="openSettings('workspace', 1)"
        >
          <div class="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-[var(--color-accent)]/10 text-[var(--color-accent)]">
            <FolderOpenIcon class="h-4 w-4" />
          </div>
          <div
            class="overflow-hidden whitespace-nowrap transition-all duration-300 ease-in-out"
            :class="appStore.isSidebarCollapsed ? 'max-w-0 opacity-0 ml-0' : 'max-w-[200px] opacity-100 ml-3'"
          >
            <span class="block truncate text-[13px] font-semibold leading-snug text-[var(--color-text-main)]">
              {{ activeWorkspaceName }}
            </span>
            <span class="block truncate text-[11px] leading-snug text-[var(--color-text-muted)]">
              {{ activeWorkspaceCaption }}
            </span>
          </div>
        </button>
      </div>

      <div class="mx-2 mb-2 h-px bg-[var(--color-border)] opacity-60" />

      <!-- Conversations Section -->
      <div class="flex min-h-0 flex-1 flex-col">
        <!-- Section Header -->
        <div class="flex h-10 w-full items-center px-3">
          <!-- Collapsed State: Plus icon mathematically locked to the center axis -->
          <div class="flex h-6 w-6 shrink-0 items-center justify-center transition-opacity duration-200"
               :class="appStore.isSidebarCollapsed ? 'opacity-100 pointer-events-auto' : 'opacity-0 absolute pointer-events-none'">
            <button @click.stop="createConversation" class="flex h-full w-full items-center justify-center rounded-md text-[var(--color-text-muted)] hover:bg-[var(--color-text-main)]/10 hover:text-[var(--color-text-main)] focus:outline-none" title="New Conversation">
              <PlusIcon class="h-4 w-4" />
            </button>
          </div>
          
          <!-- Expanded State -->
          <div
            class="flex flex-1 items-center justify-between overflow-hidden whitespace-nowrap transition-all duration-300 ease-in-out"
            :class="appStore.isSidebarCollapsed ? 'max-w-0 opacity-0 ml-0' : 'max-w-[200px] opacity-100 ml-0'"
          >
            <span class="text-[11px] font-semibold uppercase tracking-widest text-[var(--color-text-muted)] opacity-80">Chats</span>
            <button
              v-if="appStore.hasWorkspace"
              type="button"
              class="flex h-6 w-6 items-center justify-center rounded-md text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-text-main)]/10 hover:text-[var(--color-text-main)] focus:outline-none"
              title="New Conversation"
              @click.stop="createConversation"
            >
              <PlusIcon class="h-4 w-4" />
            </button>
          </div>
        </div>

        <!-- Conversation List -->
        <div class="flex-1 overflow-y-auto overflow-x-hidden pb-2">
          <div v-if="!appStore.hasWorkspace" class="px-3 py-2 text-[12px] text-[var(--color-text-muted)] transition-opacity" :class="appStore.isSidebarCollapsed ? 'opacity-0' : 'opacity-100'">
            Create a workspace to start.
          </div>
          
          <div v-else class="space-y-0.5 mt-1">
            <div
              v-for="conv in filteredConversations"
              :key="conv.id"
              class="group relative flex items-center rounded-lg cursor-pointer transition-colors hover:bg-[var(--color-text-main)]/5 px-3 py-2"
              :class="appStore.activeConversationId === conv.id ? 'bg-[var(--color-selected-surface)]' : ''"
              @click="selectConversation(conv.id)"
            >
              <!-- Active Indicator Line -->
              <div
                v-if="appStore.activeConversationId === conv.id"
                class="absolute left-0 top-1/2 -translate-y-1/2 h-1/2 w-[3px] rounded-r-full bg-[var(--color-accent)] transition-all"
              />

              <!-- Editing State -->
              <div v-if="editingId === conv.id" class="flex w-full items-center pl-9" @click.stop>
                <input
                  :ref="(el) => { if (el) editInputs[conv.id] = el }"
                  v-model="editingTitleValue"
                  class="w-full rounded border border-[var(--color-accent)] bg-[var(--color-surface)] px-2 py-1 text-[13px] text-[var(--color-text-main)] outline-none"
                  @keydown.enter.prevent="saveTitle(conv.id)"
                  @keydown.esc.prevent="cancelEditing"
                  @blur="saveTitle(conv.id)"
                />
              </div>

              <!-- Display State -->
              <template v-else>
                <!-- Universal Dot Indicator -->
                <div class="flex h-6 w-6 shrink-0 items-center justify-center text-[var(--color-text-muted)] group-hover:text-[var(--color-text-main)]">
                  <div class="h-[6px] w-[6px] rounded-full transition-colors duration-200" :class="appStore.activeConversationId === conv.id ? 'bg-[var(--color-accent)]' : 'bg-current opacity-40 group-hover:opacity-100'" />
                </div>

                <div
                  class="overflow-hidden whitespace-nowrap transition-all duration-300 ease-in-out"
                  :class="appStore.isSidebarCollapsed ? 'max-w-0 opacity-0 ml-0' : 'flex-1 max-w-[200px] opacity-100 ml-3'"
                >
                  <p
                    class="truncate text-[13px]"
                    :class="appStore.activeConversationId === conv.id ? 'font-medium text-[var(--color-text-main)]' : 'text-[var(--color-text-muted)] group-hover:text-[var(--color-text-main)]'"
                    :title="conv.title || 'Untitled'"
                  >
                    {{ conv.title || 'Untitled' }}
                  </p>
                </div>

                <!-- Ellipsis Menu Button -->
                <div class="relative shrink-0 transition-opacity pl-2" :class="appStore.isSidebarCollapsed ? 'hidden' : 'opacity-0 group-hover:opacity-100'">
                  <button
                    type="button"
                    class="flex h-6 w-6 items-center justify-center rounded-md text-[var(--color-text-muted)] hover:bg-[var(--color-surface)] hover:text-[var(--color-text-main)] focus:outline-none"
                    @click.stop="toggleConversationMenu(conv.id)"
                  >
                    <EllipsisHorizontalIcon class="h-4 w-4" />
                  </button>

                  <!-- Floating Menu -->
                  <div
                    v-if="conversationMenuId === conv.id"
                    class="absolute right-0 top-7 z-50 w-32 rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-elevated)] py-1 shadow-lg"
                  >
                    <button @click.stop="startEditingFromMenu(conv)" class="w-full px-3 py-1.5 text-left text-[12px] font-medium text-[var(--color-text-main)] hover:bg-[var(--color-panel-muted)] transition-colors">Rename</button>
                    <button @click.stop="confirmDeleteConversation(conv.id)" class="w-full px-3 py-1.5 text-left text-[12px] font-medium text-[var(--color-danger)] hover:bg-[var(--color-danger-bg)] transition-colors">Delete</button>
                  </div>
                </div>
              </template>
            </div>
          </div>
        </div>
      </div>

      <!-- Footer Navigation -->
      <nav class="mt-auto pb-4 pt-2">
        <div class="mx-2 mb-2 h-px bg-[var(--color-border)] opacity-60" />
        <div class="flex flex-col space-y-0.5">
          <!-- API Keys -->
          <button
            type="button"
            class="flex w-full items-center rounded-lg px-3 py-2 text-left text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-text-main)]/5 hover:text-[var(--color-text-main)] focus:outline-none"
            title="API Keys"
            @click="openSettings('llm')"
          >
            <div class="flex h-6 w-6 shrink-0 items-center justify-center">
              <KeyIcon class="h-5 w-5" />
            </div>
            <div
              class="overflow-hidden whitespace-nowrap transition-all duration-300 ease-in-out"
              :class="appStore.isSidebarCollapsed ? 'max-w-0 opacity-0 ml-0' : 'max-w-[200px] opacity-100 ml-3'"
            >
              <span class="text-[13px] font-medium">API Keys</span>
            </div>
          </button>

          <!-- Profile -->
          <div class="relative">
            <button
              ref="profileMenuButtonRef"
              type="button"
              class="flex w-full items-center rounded-lg px-3 py-2 text-left transition-colors hover:bg-[var(--color-text-main)]/5 focus:outline-none"
              :class="profileMenuOpen ? 'bg-[var(--color-text-main)]/5 text-[var(--color-text-main)]' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-main)]'"
              title="Profile Settings"
              @click="toggleProfileMenu"
            >
              <div class="flex h-6 w-6 shrink-0 items-center justify-center">
                <UserCircleIcon class="h-5 w-5" />
              </div>
              <div
                class="overflow-hidden whitespace-nowrap transition-all duration-300 ease-in-out"
                :class="appStore.isSidebarCollapsed ? 'max-w-0 opacity-0 ml-0' : 'max-w-[200px] opacity-100 ml-3'"
              >
                <span class="text-[13px] font-medium">Profile</span>
              </div>
            </button>

            <!-- Profile Popup -->
            <div
              v-if="profileMenuOpen"
              ref="profileMenuRef"
              class="absolute bottom-full left-[60px] mb-2 z-50 w-48 overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-panel-elevated)] shadow-lg"
            >
              <button @click="openProfileSection('account')" class="w-full px-3 py-2 text-left text-[13px] font-medium text-[var(--color-text-main)] hover:bg-[var(--color-panel-muted)] transition-colors">Account Settings</button>
              <button @click="openProfileSection('appearance')" class="w-full px-3 py-2 text-left text-[13px] font-medium text-[var(--color-text-main)] hover:bg-[var(--color-panel-muted)] transition-colors">Theme Preference</button>
              <div class="h-px bg-[var(--color-border)] my-1 opacity-60" />
              <button @click="openProfileSection('terms')" class="w-full px-3 py-2 text-left text-[13px] font-medium text-[var(--color-text-main)] hover:bg-[var(--color-panel-muted)] transition-colors">Legal & Terms</button>
            </div>
          </div>
        </div>
      </nav>
    </div>

    <SettingsModal v-model="isSettingsOpen" :initial-tab="settingsInitialTab" :initial-step="settingsInitialStep" />
    <ConfirmationModal :is-open="isDeleteDialogOpen" :title="deleteDialogTitle" :message="deleteDialogMessage" confirm-text="Delete" @close="closeDeleteDialog" @confirm="confirmDelete" />
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
  PlusIcon,
  EllipsisHorizontalIcon,
  KeyIcon,
  UserCircleIcon,
} from '@heroicons/vue/24/outline'

const appStore = useAppStore()
const isSaving = ref(false)

const searchQuery = ref('')
const editingId = ref(null)
const editingTitleValue = ref('')
const editInputs = ref({})
const conversationMenuId = ref('')
const profileMenuOpen = ref(false)
const profileMenuRef = ref(null)
const profileMenuButtonRef = ref(null)

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
  if (editingId.value !== id || isSaving.value) return
  const newTitle = editingTitleValue.value.trim()
  const conv = appStore.conversations.find((c) => c.id === id)
  
  if (!newTitle || newTitle === (conv?.title || 'Untitled')) {
    cancelEditing()
    return
  }

  isSaving.value = true
  try {
    if (id === appStore.activeConversationId) {
      await appStore.updateConversationTitle(newTitle)
    } else {
      const updated = await apiService.v1UpdateConversation(id, newTitle)
      const idx = appStore.conversations.findIndex((c) => c.id === id)
      if (idx !== -1) appStore.conversations[idx] = { ...appStore.conversations[idx], title: updated.title }
    }
  } catch (error) {
    toast.error('Rename Failed', extractApiErrorMessage(error, 'Failed to update title'))
  } finally {
    isSaving.value = false
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

async function confirmDelete() {
  if (!pendingDeleteId.value) return
  try {
    if (pendingDeleteType.value === 'conversation') {
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
  } catch { /* recovery handled by parent */ }
  window.addEventListener('dataset-switched', handleDatasetCatalogChanged)
  window.addEventListener('sidebar-open-settings', handleOpenSettingsRequest)
  window.addEventListener('click', handleGlobalClick)
})

onUnmounted(() => {
  window.removeEventListener('dataset-switched', handleDatasetCatalogChanged)
  window.removeEventListener('sidebar-open-settings', handleOpenSettingsRequest)
  window.removeEventListener('click', handleGlobalClick)
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
.sidebar-root {
  will-change: width;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: color-mix(in srgb, var(--color-border) 70%, transparent);
  border-radius: 4px;
}
.custom-scrollbar:hover::-webkit-scrollbar-thumb {
  background: color-mix(in srgb, var(--color-border) 100%, transparent);
}
</style>