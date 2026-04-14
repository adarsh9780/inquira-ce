<template>
  <div
    class="flex h-full min-h-0 flex-col shrink-0 z-40 relative overflow-hidden"
    style="background-color: var(--color-sidebar-surface);"
  >
    <!-- Header with Persistent Logo -->
    <div
      class="sidebar-brand-shell h-14 shrink-0 border-b"
      style="border-color: var(--color-border);"
    >
      <button
        class="h-full w-full px-2 transition-colors duration-150"
        :class="appStore.isSidebarCollapsed ? 'justify-center' : 'justify-start'"
        style="color: var(--color-text-main);"
        :title="appStore.isSidebarCollapsed ? 'Sidebar collapsed' : 'Collapse sidebar'"
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

    <!-- Scrollable Content -->
    <div class="flex-1 overflow-y-auto overflow-x-hidden flex flex-col custom-scrollbar">
      <div
        v-show="appStore.isSidebarCollapsed"
        class="px-1 py-3 flex flex-col items-center gap-2"
      >
        <button
          type="button"
          class="sidebar-rail-btn"
          :class="{ 'sidebar-rail-btn-active': appStore.activeTab === 'workspace' }"
          title="Open datasets sidebar"
          aria-label="Open datasets sidebar"
          @click="expandSidebarFromIcon('datasets')"
        >
          <CircleStackIcon class="h-4 w-4" />
        </button>
        <button
          type="button"
          class="sidebar-rail-btn"
          :class="{ 'sidebar-rail-btn-active': appStore.activeTab === 'workspace' }"
          title="Open conversations sidebar"
          aria-label="Open conversations sidebar"
          @click="expandSidebarFromIcon('conversations')"
        >
          <ChatBubbleLeftRightIcon class="h-4 w-4" />
        </button>
        <button
          type="button"
          class="sidebar-rail-btn"
          :class="{ 'sidebar-rail-btn-active': appStore.activeTab === 'schema-editor' }"
          title="Open schema editor"
          aria-label="Open schema editor"
          @click="openSchemaFromRail"
        >
          <DocumentTextIcon class="h-4 w-4" />
        </button>
      </div>

      <div v-show="!appStore.isSidebarCollapsed" class="px-3 py-3 space-y-2">
        <!-- Workspaces Section -->
        <div class="space-y-1">
          <!-- Section Header -->
          <button
            @click="workspacesExpanded = !workspacesExpanded"
            class="w-full flex items-center justify-between px-2 py-1.5 rounded-lg transition-colors hover:bg-[var(--color-surface)]"
          >
            <div class="flex items-center gap-2 min-w-0">
              <FolderOpenIcon v-if="workspacesExpanded" class="w-4 h-4 shrink-0" style="color: var(--color-text-main);" />
              <FolderIcon v-else class="w-4 h-4 shrink-0" style="color: var(--color-text-muted);" />
              <span class="text-[15px] font-bold leading-[1.3] truncate" style="color: var(--color-text-main);">{{ workspaceHeaderLabel }}</span>
            </div>
          </button>

          <!-- Section Content -->
          <div v-show="workspacesExpanded" class="pl-2">
            <div v-if="appStore.workspaceDeletionJobs.length > 0" class="mb-2 px-2.5 py-2 rounded-lg text-[11px] flex items-center gap-2" style="background-color: color-mix(in srgb, var(--color-warning) 15%, transparent); color: var(--color-warning);">
              <svg class="animate-spin h-3 w-3 shrink-0" viewBox="0 0 24 24" fill="none">
                <circle class="opacity-30" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-90" d="M22 12a10 10 0 0 1-10 10" stroke="currentColor" stroke-width="4" />
              </svg>
              <span class="truncate">Deleting workspace...</span>
            </div>

            <div v-if="appStore.workspaces.length === 0" class="px-2 py-2 text-xs" style="color: var(--color-text-muted);">
              No workspaces yet
            </div>
          </div>
        </div>

        <!-- Datasets Section -->
        <div
          v-if="appStore.hasWorkspace && workspacesExpanded"
          class="space-y-1 pl-2"
        >
          <!-- Section Header -->
          <div class="group flex items-center justify-between px-2 py-1">
            <div class="flex items-center gap-2 min-w-0">
              <CircleStackIcon class="w-4 h-4 shrink-0" style="color: var(--color-text-muted);" title="Datasets" />
              <p class="section-label truncate">Datasets</p>
            </div>
            <button
              v-if="appStore.hasWorkspace"
              @click.stop="openSettings('workspace', 2)"
              class="btn-icon shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
              title="Add Dataset"
            >
              <PlusIcon class="w-3.5 h-3.5" />
            </button>
          </div>

          <!-- Section Content -->
          <div v-show="datasetsExpanded" class="pl-4">
            <div v-if="isLoadingDatasets" class="px-2 py-2 text-xs text-center flex items-center justify-center gap-2" style="color: var(--color-text-muted);">
              <div class="animate-spin w-3 h-3 border-2 rounded-full" style="border-color: var(--color-border); border-top-color: var(--color-text-muted);"></div>
              <span>Loading datasets...</span>
            </div>

            <div v-else-if="filteredDatasets.length === 0 && localDatasets.length > 0" class="px-2 py-2 text-xs" style="color: var(--color-text-muted);">
              No matches found
            </div>

            <div v-else-if="localDatasets.length === 0" class="px-2 py-2 text-xs" style="color: var(--color-text-muted);">
              No datasets yet
            </div>

            <div v-else class="space-y-0.5 pb-0.5">
              <div
                v-for="ds in filteredDatasets"
                :key="ds.table_name"
                class="group sidebar-item-row"
                :class="{ 'sidebar-item-row-active': isSelectedDataset(ds) }"
                :title="datasetRowTitle(ds)"
                @click="selectDataset(ds)"
              >
                <div class="min-w-0 flex-1">
                  <p
                    class="truncate text-[13px] font-medium leading-[1.4]"
                    :class="isSelectedDataset(ds) ? 'text-[var(--color-accent)]' : ''"
                    style="color: var(--color-text-main);"
                  >
                    {{ datasetFriendlyName(ds.table_name) }}
                  </p>
                  <p
                    v-if="ds.file_path"
                    class="truncate text-[12px] font-normal leading-[1.3]"
                    :class="isSelectedDataset(ds) ? 'text-[var(--color-accent)] opacity-75' : ''"
                    style="color: var(--color-text-muted);"
                    :title="ds.file_path"
                  >
                    {{ datasetSourceCaption(ds.file_path) }}
                  </p>
                </div>
                <button
                  @click.stop="confirmDeleteDataset(ds.table_name)"
                  class="btn-icon p-1 rounded transition-all duration-150 opacity-0 group-hover:opacity-100 shrink-0"
                  style="color: var(--color-text-muted);"
                  title="Delete Dataset"
                >
                  <TrashIcon class="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Conversations Section -->
        <div
          v-if="appStore.hasWorkspace && workspacesExpanded"
          class="space-y-1 pl-2"
        >
          <!-- Section Header -->
          <div class="group flex items-center justify-between px-2 py-1">
            <div class="flex items-center gap-2 min-w-0">
              <ChatBubbleLeftRightIcon class="w-4 h-4 shrink-0" style="color: var(--color-text-muted);" />
              <p class="section-label truncate">Conversations</p>
            </div>
            <button
              v-if="appStore.hasWorkspace"
              @click.stop="createConversation"
              class="btn-icon shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
              title="New Conversation"
            >
              <PlusIcon class="w-3.5 h-3.5" />
            </button>
          </div>

          <!-- Section Content -->
          <div v-show="conversationsExpanded" class="pl-4">
            <div v-if="filteredConversations.length === 0 && appStore.conversations.length > 0" class="px-2 py-2 text-xs" style="color: var(--color-text-muted);">
              No matches found
            </div>

            <div v-if="appStore.conversations.length === 0" class="px-2 py-2 text-xs" style="color: var(--color-text-muted);">
              No conversations yet
            </div>

            <div v-else class="space-y-0.5 pb-0.5">
              <div
                v-for="conv in filteredConversations"
                :key="conv.id"
                class="group sidebar-item-row"
                :class="{ 'sidebar-item-row-active': appStore.activeConversationId === conv.id }"
                @click="selectConversation(conv.id)"
              >
                <div class="flex items-center min-w-0 pr-2 flex-1" @dblclick="startEditing(conv)">
                  <div class="flex-1 min-w-0">
                    <div v-if="editingId === conv.id" class="flex items-center gap-1 w-full relative z-10">
                      <input
                        :ref="(el) => { if (el) editInputs[conv.id] = el }"
                        v-model="editingTitleValue"
                        class="input-base py-0.5 px-1 text-[13px] font-medium"
                        @keydown.enter.prevent="saveTitle(conv.id)"
                        @keydown.esc.prevent="cancelEditing"
                        @blur="saveTitle(conv.id)"
                        @click.stop
                      />
                    </div>
                    <template v-else>
                      <p
                        class="truncate text-[13px] leading-[1.4]"
                        :class="conv.id === appStore.activeConversationId ? 'text-[var(--color-accent)] font-medium' : 'font-normal'"
                        :title="conv.title || 'Untitled'"
                      >
                        {{ conv.title || 'Untitled' }}
                      </p>
                    </template>
                  </div>
                </div>
                <div v-if="editingId !== conv.id" class="relative flex-shrink-0 flex items-center opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    @click.stop="toggleConversationMenu(conv.id)"
                    class="btn-icon p-1 rounded hover:text-[var(--color-accent)]"
                    style="color: var(--color-text-muted);"
                    title="Conversation actions"
                  >
                    <EllipsisHorizontalIcon class="w-3.5 h-3.5" />
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
                      class="w-full px-3 py-2 text-left text-xs font-medium transition-colors hover:bg-red-50"
                      style="color: #dc2626;"
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
    </div>

    <!-- Search Bar (Animated) -->
    <Transition name="search-bar">
      <div v-if="isSearchOpen && !appStore.isSidebarCollapsed" class="px-3 py-3 border-t" style="border-color: var(--color-border);">
        <div class="relative">
          <MagnifyingGlassIcon class="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 pointer-events-none" style="color: var(--color-text-muted);" />
          <input
            ref="searchInputRef"
            v-model="searchQuery"
            type="text"
            placeholder="Search..."
            class="w-full pl-9 pr-3 py-2 text-[14px] rounded-lg border transition-all duration-150 placeholder:text-[var(--color-text-muted)] focus:outline-none focus:ring-2"
            style="background-color: var(--color-surface); border-color: var(--color-border); color: var(--color-text-main); --tw-ring-color: var(--color-accent);"
          />
          <button
            v-if="searchQuery"
            @click="searchQuery = ''"
            class="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 rounded hover:bg-[var(--color-border)] transition-colors"
          >
            <XMarkIcon class="w-3 h-3" style="color: var(--color-text-muted);" />
          </button>
        </div>
      </div>
    </Transition>

    <!-- Footer Icons -->
    <div
      class="border-t p-2 shrink-0 flex items-center justify-center gap-2"
      :class="appStore.isSidebarCollapsed ? 'flex-col' : 'flex-row'"
      style="border-color: var(--color-border); background-color: var(--color-sidebar-surface);"
    >
      <button
        @click="openSettings('workspace', 1)"
        class="flex items-center justify-center p-2 rounded-lg transition-all duration-200 hover:bg-[var(--color-surface)]"
        style="color: var(--color-text-main);"
        title="Create Workspace"
        aria-label="Create Workspace"
      >
        <FolderPlusIcon class="w-4 h-4" />
      </button>

      <button
        @click="openSettings('api')"
        class="flex items-center justify-center p-2 rounded-lg transition-all duration-200 hover:bg-[var(--color-surface)]"
        style="color: var(--color-text-main);"
        title="Settings"
        aria-label="Settings"
      >
        <CogIcon class="w-4 h-4" />
      </button>

      <button
        @click="toggleSearch"
        class="flex items-center justify-center p-2 rounded-lg transition-all duration-200 hover:bg-[var(--color-surface)]"
        style="color: var(--color-text-main);"
        title="Search"
        aria-label="Search"
      >
        <MagnifyingGlassIcon class="w-4 h-4" />
      </button>

      <button
        @click="openTerms"
        class="flex items-center justify-center p-2 rounded-lg transition-all duration-200 hover:bg-[var(--color-surface)]"
        style="color: var(--color-text-main);"
        title="Terms & Conditions"
        aria-label="Terms & Conditions"
      >
        <ScaleIcon class="w-4 h-4" />
      </button>
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

    <div
      v-if="isTermsDialogOpen"
      class="fixed inset-0 z-[70] flex items-center justify-center px-4"
      @click="closeTermsDialog"
    >
      <div class="absolute inset-0 bg-black/10 backdrop-blur-[1.5px]"></div>
      <div
        class="relative w-full max-w-3xl rounded-xl border shadow-2xl"
        style="background-color: var(--color-surface); border-color: var(--color-border); color: var(--color-text-main);"
        @click.stop
      >
        <div class="flex items-center justify-between border-b px-5 py-3" style="border-color: var(--color-border);">
          <div>
            <p class="text-sm font-semibold">Terms & Conditions</p>
            <p v-if="termsLastUpdated" class="text-xs" style="color: var(--color-text-muted);">Last updated: {{ termsLastUpdated }}</p>
          </div>
          <button
            class="h-7 w-7 p-1.5 rounded border"
            style="border-color: var(--color-border); color: var(--color-text-main); background-color: var(--color-base);"
            title="Close terms"
            aria-label="Close terms"
            @click="closeTermsDialog"
          >
            <XMarkIcon class="h-4 w-4" />
          </button>
        </div>
        <div class="max-h-[70vh] overflow-y-auto px-5 py-4 text-sm leading-6">
          <p v-if="isTermsLoading" style="color: var(--color-text-muted);">Loading terms...</p>
          <p v-else-if="termsError" class="rounded-md border px-3 py-2 text-xs text-red-700 bg-red-50" style="border-color: #fca5a5;">
            {{ termsError }}
          </p>
          <div
            v-else
            class="terms-markdown-content"
            v-html="termsHtml"
          ></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'
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
  FolderIcon,
  FolderOpenIcon,
  FolderPlusIcon,
  PlusIcon,
  TrashIcon,
  EllipsisHorizontalIcon,
  CogIcon,
  ScaleIcon,
  XMarkIcon,
  MagnifyingGlassIcon,
  CircleStackIcon,
  ChatBubbleLeftRightIcon,
  DocumentTextIcon,
} from '@heroicons/vue/24/outline'

const appStore = useAppStore()

// Search
const searchQuery = ref('')
const isSearchOpen = ref(false)

// Conversation editing
const editingId = ref(null)
const editingTitleValue = ref('')
const editInputs = ref({})
const conversationMenuId = ref('')
const searchInputRef = ref(null)

function toggleSearch() {
  if (appStore.isSidebarCollapsed) {
    appStore.setSidebarCollapsed(false)
  }
  isSearchOpen.value = !isSearchOpen.value
  if (isSearchOpen.value) {
    nextTick(() => {
      searchInputRef.value?.focus()
    })
  } else {
    searchQuery.value = ''
  }
}

function handleBrandClick() {
  if (!appStore.isSidebarCollapsed) {
    appStore.setSidebarCollapsed(true)
  }
}

function expandSidebarFromIcon(target = '') {
  appStore.setActiveTab('workspace')
  appStore.setSidebarCollapsed(false)
  const normalized = String(target || '').trim().toLowerCase()
  if (normalized === 'conversations') {
    workspacesExpanded.value = true
    conversationsExpanded.value = true
    return
  }
  if (normalized === 'datasets') {
    workspacesExpanded.value = true
    datasetsExpanded.value = true
  }
}

function openSchemaFromRail() {
  appStore.setActiveTab('schema-editor')
}

// Section expansion states
const workspacesExpanded = ref(true)
const datasetsExpanded = ref(true)
const conversationsExpanded = ref(true)

// Local datasets state (fetched via API, not in appStore)
const localDatasets = ref([])
const isLoadingDatasets = ref(false)

// Settings dialog
const isSettingsOpen = ref(false)
const settingsInitialTab = ref('llm')
const settingsInitialStep = ref(1)

// Terms dialog
const isTermsDialogOpen = ref(false)
const isTermsLoading = ref(false)
const termsError = ref('')
const termsMarkdown = ref('')
const termsLastUpdated = ref('')

// Delete confirmation
const isDeleteDialogOpen = ref(false)
const deleteDialogTitle = ref('')
const deleteDialogMessage = ref('')
const pendingDeleteType = ref('')
const pendingDeleteId = ref('')
const datasetDeletionPollers = new Map()

const termsMarkdownRenderer = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
})

const termsHtml = computed(() => {
  const raw = String(termsMarkdown.value || '').trim()
  if (!raw) return ''
  return DOMPurify.sanitize(termsMarkdownRenderer.render(raw), {
    USE_PROFILES: { html: true },
  })
})

// Filtered lists
const filteredDatasets = computed(() => {
  if (!searchQuery.value) return localDatasets.value
  const query = searchQuery.value.toLowerCase()
  return localDatasets.value.filter((ds) => {
    const rawName = String(ds?.table_name || '').toLowerCase()
    const friendlyName = datasetFriendlyName(ds?.table_name).toLowerCase()
    return rawName.includes(query) || friendlyName.includes(query)
  })
})

const filteredConversations = computed(() => {
  if (!searchQuery.value) return appStore.conversations
  const query = searchQuery.value.toLowerCase()
  return appStore.conversations.filter(conv => conv.title?.toLowerCase().includes(query))
})

// Selected workspace
const activeWorkspaceName = computed(() => {
  const activeId = String(appStore.activeWorkspaceId || '').trim()
  const activeWorkspace = appStore.workspaces.find((ws) => ws.id === activeId)
  return activeWorkspace?.name || 'Choose a workspace'
})
const workspaceHeaderLabel = computed(() => {
  if (appStore.hasWorkspace) return activeWorkspaceName.value
  return 'Workspace'
})

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

// Fetch datasets from API
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
    const catalogDatasets = workspaceDatasets.map((item) => ({
      table_name: item.table_name,
      file_path: item.source_path,
    })).filter((item) => Boolean(String(item.table_name || '').trim()))
    localDatasets.value = catalogDatasets
  } catch (error) {
    console.error('Failed to load datasets:', error)
    localDatasets.value = []
  } finally {
    isLoadingDatasets.value = false
  }
}

function handleDatasetCatalogChanged() {
  // Data uploads can happen inside modal flows that keep the same workspace id.
  // Without this listener, UnifiedSidebar only refreshes on workspace switches,
  // leaving users with a stale dataset list until restart or manual context hop.
  if (!appStore.hasWorkspace || !appStore.activeWorkspaceId) return
  void fetchDatasets()
}

function handleOpenSettingsRequest(event) {
  const requestedTab = String(event?.detail?.tab || 'api').trim() || 'api'
  const requestedStep = Number(event?.detail?.step || 1)
  openSettings(requestedTab, requestedStep)
}

async function selectWorkspace(id) {
  if (!id || id === appStore.activeWorkspaceId) {
    return
  }
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
      detail: { tableName: selectedTableName, dataPath: selectedPath }
    }))
  } catch (error) {
    console.error('Failed to switch dataset:', error)
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

function handleConversationMenuOutsideClick(event) {
  const target = event?.target
  if (!(target instanceof Element)) return
  if (target.closest('[data-conversation-actions-menu]')) return
  closeConversationMenu()
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

// Settings
function openSettings(tab = 'llm', step = 1) {
  const normalized = String(tab || '').trim().toLowerCase()
  if (normalized === 'api') {
    settingsInitialTab.value = 'llm'
  } else if (normalized === 'workspace') {
    settingsInitialTab.value = 'workspace'
  } else if (normalized === 'data') {
    settingsInitialTab.value = 'workspace'
  } else if (normalized === 'account') {
    settingsInitialTab.value = 'account'
  } else {
    settingsInitialTab.value = 'llm'
  }
  const parsedStep = Number(step)
  settingsInitialStep.value = Number.isFinite(parsedStep) && parsedStep >= 1 ? Math.floor(parsedStep) : 1
  isSettingsOpen.value = true
}

// Terms
async function loadTermsAndConditions({ force = false } = {}) {
  if (termsMarkdown.value && !force) return
  isTermsLoading.value = true
  termsError.value = ''
  try {
    const payload = await apiService.v1GetTermsAndConditions()
    termsMarkdown.value = String(payload?.markdown || '').trim()
    termsLastUpdated.value = String(payload?.last_updated || '').trim()
  } catch (error) {
    termsError.value = error?.message || 'Failed to load Terms & Conditions.'
  } finally {
    isTermsLoading.value = false
  }
}

async function openTerms() {
  isTermsDialogOpen.value = true
  await loadTermsAndConditions()
}

function closeTermsDialog() {
  isTermsDialogOpen.value = false
}

// Delete confirmations
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

// Bootstrap
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
  window.addEventListener('click', handleConversationMenuOutsideClick)
})

onUnmounted(() => {
  window.removeEventListener('dataset-switched', handleDatasetCatalogChanged)
  window.removeEventListener('sidebar-open-settings', handleOpenSettingsRequest)
  window.removeEventListener('click', handleConversationMenuOutsideClick)
  stopDatasetDeletionPollers()
})

// Watch for workspace changes to fetch datasets and conversations
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
    isSearchOpen.value = false
    searchQuery.value = ''
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

/* Search bar animation */
.search-bar-enter-active,
.search-bar-leave-active {
  transition: all 0.2s ease;
}

.search-bar-enter-from,
.search-bar-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

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

.sidebar-rail-btn {
  width: 2rem;
  height: 2rem;
  border-radius: 0.5rem;
  border: 1px solid transparent;
  color: var(--color-text-muted);
  background: transparent;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: background-color 140ms ease, border-color 140ms ease, color 140ms ease;
}

.sidebar-rail-btn:hover {
  background-color: color-mix(in srgb, var(--color-text-main) 6%, transparent);
  border-color: var(--color-border);
  color: var(--color-text-main);
}

.sidebar-rail-btn-active {
  color: #C96A2E;
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

:deep(.terms-markdown-content h1),
:deep(.terms-markdown-content h2),
:deep(.terms-markdown-content h3) {
  margin-top: 1rem;
  margin-bottom: 0.5rem;
  font-weight: 700;
}

:deep(.terms-markdown-content h1:first-child),
:deep(.terms-markdown-content h2:first-child),
:deep(.terms-markdown-content h3:first-child) {
  margin-top: 0;
}

:deep(.terms-markdown-content p) {
  margin: 0.5rem 0;
}

:deep(.terms-markdown-content ul) {
  margin: 0.5rem 0;
  padding-left: 1.1rem;
  list-style: disc;
}

:deep(.terms-markdown-content li) {
  margin: 0.2rem 0;
}

:deep(.terms-markdown-content code) {
  background-color: color-mix(in srgb, var(--color-text-main) 10%, transparent);
  border-radius: 0.25rem;
  padding: 0.05rem 0.3rem;
}

:deep(.terms-markdown-content a) {
  color: #2563eb;
  text-decoration: underline;
}
</style>
