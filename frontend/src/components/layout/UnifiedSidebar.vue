<template>
  <div
    class="relative z-40 flex h-full w-full min-h-0 min-w-0 flex-col overflow-hidden sidebar-root"
  >
    <!-- ─── Brand / Collapse Toggle ─── -->
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

    <!-- ─── Main Scroll Area ─── -->
    <div class="flex min-h-0 flex-1 flex-col overflow-x-hidden px-2 custom-scrollbar">

      <!-- Active Workspace -->
      <div class="pt-3 pb-2">
        <button
          type="button"
          class="flex w-full items-center rounded-lg py-2 text-left transition-colors hover:bg-[var(--color-text-main)]/5 focus:outline-none"
          :class="[
            appStore.isSidebarCollapsed ? 'justify-center px-0' : 'justify-start px-3',
            'text-[var(--color-text-muted)]',
          ]"
          :title="appStore.isSidebarCollapsed ? activeWorkspaceName : 'Open workspace settings'"
          @click="openSettings('workspace', 1)"
        >
          <div class="flex h-6 w-6 shrink-0 items-center justify-center">
            <FolderOpenIcon class="h-5 w-5 text-[var(--color-text-main)]" />
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

      <div class="mx-1 mb-2 h-px bg-[var(--color-border)] opacity-60" />

      <!-- ─── Conversations ─── -->
      <div class="flex min-h-0 flex-1 flex-col">

        <!-- Section Header -->
        <div
          class="flex h-10 w-full items-center transition-all duration-300"
          :class="appStore.isSidebarCollapsed ? 'justify-center px-0' : 'justify-between px-3'"
        >
          <!-- Collapsed: just the plus icon centered -->
          <button
            v-if="appStore.isSidebarCollapsed && appStore.hasWorkspace"
            type="button"
            class="flex h-6 w-6 items-center justify-center rounded-md text-[var(--color-text-muted)] hover:bg-[var(--color-text-main)]/10 hover:text-[var(--color-text-main)] focus:outline-none transition-colors"
            title="New Conversation"
            @click.stop="createConversation"
          >
            <PlusIcon class="h-4 w-4" />
          </button>

          <!-- Expanded: label + plus -->
          <template v-if="!appStore.isSidebarCollapsed">
            <span class="text-[11px] font-semibold uppercase tracking-widest text-[var(--color-text-muted)] opacity-80">
              Chats
            </span>
            <button
              v-if="appStore.hasWorkspace"
              type="button"
              class="flex h-6 w-6 items-center justify-center rounded-md text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-text-main)]/10 hover:text-[var(--color-text-main)] focus:outline-none"
              title="New Conversation"
              @click.stop="createConversation"
            >
              <PlusIcon class="h-4 w-4" />
            </button>
          </template>
        </div>

        <!-- Conversation List -->
        <div class="max-h-[11.75rem] flex-none overflow-y-auto overflow-x-hidden pb-1">
          <div
            v-if="!appStore.hasWorkspace"
            class="px-3 py-2 text-[12px] text-[var(--color-text-muted)] transition-opacity"
            :class="appStore.isSidebarCollapsed ? 'opacity-0' : 'opacity-100'"
          >
            Create a workspace to start.
          </div>

          <div v-else class="space-y-0.5 mt-1">
            <div
              v-for="(conv, index) in appStore.conversations"
              :key="conv.id"
              class="group relative flex min-h-9 select-none items-center rounded-lg cursor-pointer transition-colors hover:bg-[var(--color-text-main)]/5"
              :class="[
                appStore.isSidebarCollapsed ? 'justify-center px-0 py-1.5' : 'justify-start px-3 py-1.5',
                isConversationSelected(conv.id) || appStore.activeConversationId === conv.id ? 'bg-[var(--color-selected-surface)]' : '',
              ]"
              :title="conv.title || 'Untitled'"
              @click="handleConversationClick($event, conv.id, index)"
              @contextmenu.prevent="openConversationContextMenu($event, conv.id)"
            >
              <!-- Active indicator line — only in expanded mode -->
              <div
                v-if="appStore.activeConversationId === conv.id && !appStore.isSidebarCollapsed"
                class="absolute left-0 top-1/2 -translate-y-1/2 h-1/2 w-[3px] rounded-r-full bg-[var(--color-accent)]"
              />

              <!-- Inline edit mode -->
              <div v-if="editingId === conv.id" class="flex w-full items-center gap-1 pl-9" @click.stop>
                <input
                  :ref="(el) => { if (el) editInputs[conv.id] = el }"
                  v-model="editingTitleValue"
                  class="w-full rounded border border-[var(--color-accent)] bg-[var(--color-surface)] px-2 py-1 text-[13px] text-[var(--color-text-main)] outline-none"
                  @keydown.enter.prevent="saveTitle(conv.id)"
                  @keydown.esc.prevent="cancelEditing"
                  @blur="saveTitle(conv.id)"
                />
              </div>

              <!-- Display mode -->
              <template v-else>
                <div class="flex h-6 w-6 shrink-0 items-center justify-center">
                  <span
                    class="inline-flex min-w-[1.5rem] items-center justify-center px-1 text-[11px] font-semibold leading-none tabular-nums tracking-[0.02em] transition-colors duration-200"
                    :class="isConversationSelected(conv.id) || appStore.activeConversationId === conv.id
                      ? 'text-[var(--color-accent)]'
                      : 'text-[var(--color-text-muted)] group-hover:text-[var(--color-text-main)]'"
                  >
                    {{ conversationBadgeLabel(index, appStore.conversations.length) }}
                  </span>
                </div>

                <!-- Title (hidden when collapsed) -->
                <div
                  class="overflow-hidden whitespace-nowrap transition-all duration-300 ease-in-out"
                  :class="appStore.isSidebarCollapsed ? 'max-w-0 opacity-0 ml-0' : 'flex-1 max-w-[200px] opacity-100 ml-3'"
                >
                  <p
                    class="truncate text-[13px]"
                    :class="isConversationSelected(conv.id) || appStore.activeConversationId === conv.id
                      ? 'font-medium text-[var(--color-text-main)]'
                      : 'text-[var(--color-text-muted)] group-hover:text-[var(--color-text-main)]'"
                    :title="conv.title || 'Untitled'"
                  >
                    {{ conv.title || 'Untitled' }}
                  </p>
                </div>

                <!-- Ellipsis menu (expanded only) -->
                <div
                  v-if="!appStore.isSidebarCollapsed"
                  class="relative shrink-0 pl-2 opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <button
                    type="button"
                    class="flex h-6 w-6 items-center justify-center rounded-md text-[var(--color-text-muted)] hover:bg-[var(--color-surface)] hover:text-[var(--color-text-main)] focus:outline-none"
                    @click.stop="toggleConversationMenu($event, conv.id)"
                  >
                    <EllipsisHorizontalIcon class="h-4 w-4" />
                  </button>
                </div>
              </template>
            </div>
          </div>
        </div>
      </div>

      <!-- ─── Workspace Views ─── -->
      <nav class="flex-none pb-2 pt-2">
        <div class="flex flex-col space-y-0.5">
          <button
            type="button"
            class="flex w-full items-center rounded-lg py-2 text-left transition-colors hover:bg-[var(--color-text-main)]/5 focus:outline-none"
            :class="[
              appStore.isSidebarCollapsed ? 'justify-center px-0' : 'justify-start px-3',
              appStore.activeTab === 'schema-editor' ? 'bg-[var(--color-selected-surface)] text-[var(--color-text-main)]' : 'text-[var(--color-text-muted)]',
            ]"
            :title="appStore.isSidebarCollapsed ? 'Open schema editor' : 'Schema editor'"
            @click="openSchemaEditor"
          >
            <div class="flex h-6 w-6 shrink-0 items-center justify-center">
              <CircleStackIcon class="h-5 w-5" :class="appStore.activeTab === 'schema-editor' ? 'text-[var(--color-accent)]' : 'text-[var(--color-text-main)]'" />
            </div>
            <div
              class="overflow-hidden whitespace-nowrap transition-all duration-300 ease-in-out"
              :class="appStore.isSidebarCollapsed ? 'max-w-0 opacity-0 ml-0' : 'max-w-[200px] opacity-100 ml-3'"
            >
              <span class="block truncate text-[13px] font-medium leading-snug text-[var(--color-text-main)]">
                Schema
              </span>
              <span class="block truncate text-[11px] leading-snug text-[var(--color-text-muted)]">
                Datasets and column metadata
              </span>
            </div>
          </button>

          <button
            type="button"
            class="flex w-full items-center rounded-lg py-2 text-left transition-colors hover:bg-[var(--color-text-main)]/5 focus:outline-none"
            :class="[
              appStore.isSidebarCollapsed ? 'justify-center px-0' : 'justify-start px-3',
              appStore.activeTab === 'conversation-tree' ? 'bg-[var(--color-selected-surface)] text-[var(--color-text-main)]' : 'text-[var(--color-text-muted)]',
            ]"
            :title="appStore.isSidebarCollapsed ? 'Open conversation tree' : 'Conversation Tree'"
            @click="openConversationTree"
          >
            <div class="flex h-6 w-6 shrink-0 items-center justify-center">
              <QueueListIcon class="h-5 w-5" :class="appStore.activeTab === 'conversation-tree' ? 'text-[var(--color-accent)]' : 'text-[var(--color-text-main)]'" />
            </div>
            <div
              class="overflow-hidden whitespace-nowrap transition-all duration-300 ease-in-out"
              :class="appStore.isSidebarCollapsed ? 'max-w-0 opacity-0 ml-0' : 'max-w-[200px] opacity-100 ml-3'"
            >
              <span class="block truncate text-[13px] font-medium leading-snug text-[var(--color-text-main)]">
                Conversation Tree
              </span>
              <span class="block truncate text-[11px] leading-snug text-[var(--color-text-muted)]">
                Turns across this workspace
              </span>
            </div>
          </button>
        </div>
      </nav>

      <!-- ─── Footer Navigation ─── -->
      <nav class="mt-auto pb-4 pt-2">
        <div class="mx-1 mb-2 h-px bg-[var(--color-border)] opacity-60" />
        <div class="flex flex-col space-y-0.5">

          <button
            type="button"
            class="flex w-full items-center rounded-lg py-2 text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-text-main)]/5 hover:text-[var(--color-text-main)] focus:outline-none"
            :class="appStore.isSidebarCollapsed ? 'justify-center px-0' : 'justify-start px-3'"
            :title="appStore.isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"
            @click="handleBrandClick"
          >
            <div class="flex h-6 w-6 shrink-0 items-center justify-center">
              <ChevronDoubleRightIcon v-if="appStore.isSidebarCollapsed" class="h-5 w-5" />
              <ChevronDoubleLeftIcon v-else class="h-5 w-5" />
            </div>
            <div
              class="overflow-hidden whitespace-nowrap transition-all duration-300 ease-in-out"
              :class="appStore.isSidebarCollapsed ? 'max-w-0 opacity-0 ml-0' : 'max-w-[200px] opacity-100 ml-3'"
            >
              <span class="text-[13px] font-medium">
                {{ appStore.isSidebarCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar' }}
              </span>
            </div>
          </button>

          <!-- Settings -->
          <button
            type="button"
            class="flex w-full items-center rounded-lg py-2 text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-text-main)]/5 hover:text-[var(--color-text-main)] focus:outline-none"
            :class="appStore.isSidebarCollapsed ? 'justify-center px-0' : 'justify-start px-3'"
            title="Settings"
            @click="openSettings('llm', 1)"
          >
            <div class="flex h-6 w-6 shrink-0 items-center justify-center">
              <Cog6ToothIcon class="h-5 w-5" />
            </div>
            <div
              class="overflow-hidden whitespace-nowrap transition-all duration-300 ease-in-out"
              :class="appStore.isSidebarCollapsed ? 'max-w-0 opacity-0 ml-0' : 'max-w-[200px] opacity-100 ml-3'"
            >
              <span class="text-[13px] font-medium">Settings</span>
            </div>
          </button>

          <!-- Profile -->
          <div class="relative">
            <button
              ref="profileMenuButtonRef"
              type="button"
              class="flex w-full items-center rounded-lg py-2 transition-colors hover:bg-[var(--color-text-main)]/5 focus:outline-none"
              :class="[
                appStore.isSidebarCollapsed ? 'justify-center px-0' : 'justify-start px-3',
                profileMenuOpen
                  ? 'bg-[var(--color-text-main)]/5 text-[var(--color-text-main)]'
                  : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-main)]',
              ]"
              title="Profile Settings"
              @click="toggleProfileMenu"
            >
              <div class="flex h-6 w-6 shrink-0 items-center justify-center">
                <span class="sidebar-initials-avatar">
                  {{ profileInitials }}
                </span>
              </div>
              <div
                class="overflow-hidden whitespace-nowrap transition-all duration-300 ease-in-out"
                :class="appStore.isSidebarCollapsed ? 'max-w-0 opacity-0 ml-0' : 'max-w-[200px] opacity-100 ml-3'"
              >
                <span class="text-[13px] font-medium">{{ profileDisplayName }}</span>
              </div>
            </button>

          </div>

        </div>
      </nav>
    </div>

    <!-- ─── Modals ─── -->
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
    <Teleport to="body">
      <div
        v-if="profileMenuOpen"
        ref="profileMenuRef"
        class="sidebar-profile-menu layer-dropdown fixed w-48 overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-panel-elevated)] shadow-lg"
        :style="profileMenuStyle"
      >
        <button
          type="button"
          class="w-full px-3 py-2 text-left text-[13px] font-medium text-[var(--color-text-main)] hover:bg-[var(--color-panel-muted)] transition-colors"
          @click="openProfileSection('account')"
        >
          Account Settings
        </button>
        <button
          type="button"
          class="w-full px-3 py-2 text-left text-[13px] font-medium text-[var(--color-text-main)] hover:bg-[var(--color-panel-muted)] transition-colors"
          @click="openProfileSection('appearance')"
        >
          Theme Preference
        </button>
        <div class="h-px bg-[var(--color-border)] my-1 opacity-60" />
        <button
          type="button"
          class="w-full px-3 py-2 text-left text-[13px] font-medium text-[var(--color-text-main)] hover:bg-[var(--color-panel-muted)] transition-colors"
          @click="openProfileSection('terms')"
        >
          Legal &amp; Terms
        </button>
      </div>
    </Teleport>
    <Teleport to="body">
      <div
        v-if="conversationMenuId"
        class="fixed z-50 w-32 rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-elevated)] py-1 shadow-lg"
        :style="conversationMenuStyle"
        data-conversation-actions-menu
      >
        <button
          type="button"
          class="w-full px-3 py-1.5 text-left text-[12px] font-medium text-[var(--color-text-main)] hover:bg-[var(--color-panel-muted)] transition-colors"
          @click.stop="startEditingFromMenu(activeConversationMenuTarget)"
        >
          Rename
        </button>
        <button
          type="button"
          class="w-full px-3 py-1.5 text-left text-[12px] font-medium text-[var(--color-danger)] hover:bg-[var(--color-danger-bg)] transition-colors"
          @click.stop="confirmDeleteConversation(conversationMenuId)"
        >
          Delete
        </button>
      </div>
    </Teleport>
    <Teleport to="body">
      <div
        v-if="multiConversationMenu.open"
        class="fixed z-50 w-40 rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-elevated)] py-1 shadow-lg"
        :style="multiConversationMenuStyle"
        data-conversation-actions-menu
      >
        <button
          type="button"
          class="w-full px-3 py-1.5 text-left text-[12px] font-medium text-[var(--color-danger)] hover:bg-[var(--color-danger-bg)] transition-colors"
          @click.stop="confirmDeleteSelectedConversations"
        >
          Delete {{ selectedConversationIds.size }}
        </button>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { useAppStore } from '../../stores/appStore'
import { useAuthStore } from '../../stores/authStore'
import { toast } from '../../composables/useToast'
import { extractApiErrorMessage } from '../../utils/apiError'
import SettingsModal from '../modals/SettingsModal.vue'
import ConfirmationModal from '../modals/ConfirmationModal.vue'
import logo from '../../assets/favicon.svg'
import apiService from '../../services/apiService'

import {
  FolderOpenIcon,
  PlusIcon,
  EllipsisHorizontalIcon,
  CircleStackIcon,
  QueueListIcon,
  Cog6ToothIcon,
  ChevronDoubleLeftIcon,
  ChevronDoubleRightIcon,
} from '@heroicons/vue/24/outline'

// ─── Store ───────────────────────────────────────────────────────────────────
const appStore = useAppStore()
const authStore = useAuthStore()

// ─── UI State ────────────────────────────────────────────────────────────────
const editingId         = ref(null)
const editingTitleValue = ref('')
const editInputs        = ref({})
const isSaving          = ref(false)

const conversationMenuId   = ref(null)
const conversationMenuPosition = ref({ x: 0, y: 0 })
const selectedConversationIds = ref(new Set())
const lastSelectedConversationIndex = ref(-1)
const multiConversationMenu = ref({
  open: false,
  x: 0,
  y: 0,
})
const profileMenuOpen      = ref(false)
const profileMenuRef       = ref(null)
const profileMenuButtonRef = ref(null)
const profileMenuPosition  = ref({ left: 0, top: 0 })

// ─── Settings Modal ───────────────────────────────────────────────────────────
const isSettingsOpen      = ref(false)
const settingsInitialTab  = ref('llm')
const settingsInitialStep = ref(1)

// ─── Delete Dialog ────────────────────────────────────────────────────────────
const isDeleteDialogOpen  = ref(false)
const deleteDialogTitle   = ref('')
const deleteDialogMessage = ref('')
const pendingDeleteType   = ref('')
const pendingDeleteId     = ref('')
const pendingDeleteIds    = ref([])
const workspaceDatasetSummary = ref({
  workspaceId: '',
  count: 0,
  bytes: null,
  loading: false,
})

// ─── Computed ─────────────────────────────────────────────────────────────────
const activeWorkspaceName = computed(() => {
  const activeId = String(appStore.activeWorkspaceId || '').trim()
  if (!activeId) return 'No active workspace'
  const ws = appStore.workspaces.find((w) => w.id === activeId)
  return String(ws?.name || '').trim() || 'Untitled workspace'
})

const activeWorkspaceCaption = computed(() => {
  if (!appStore.hasWorkspace) return 'Create a workspace to begin'
  if (workspaceDatasetSummary.value.loading) return 'Loading datasets'
  const count = workspaceDatasetSummary.value.count
  const label = count === 1 ? '1 dataset' : `${count} datasets`
  const bytes = workspaceDatasetSummary.value.bytes
  const usage = Number.isFinite(bytes) ? `${formatStorage(bytes)} used` : 'storage used'
  return `${label} | ${usage}`
})

const profileDisplayName = computed(() => {
  return String(authStore.username || 'Local User').trim() || 'Local User'
})

const profileInitials = computed(() => {
  const parts = profileDisplayName.value
    .split(/\s+/)
    .map((part) => part.trim())
    .filter(Boolean)
  if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase()
  return (parts[0] || 'LU').slice(0, 2).toUpperCase()
})

const profileMenuStyle = computed(() => ({
  left: `${profileMenuPosition.value.left}px`,
  top: `${profileMenuPosition.value.top}px`,
}))

const multiConversationMenuStyle = computed(() => ({
  left: `${multiConversationMenu.value.x}px`,
  top: `${multiConversationMenu.value.y}px`,
}))

const conversationMenuStyle = computed(() => ({
  left: `${conversationMenuPosition.value.x}px`,
  top: `${conversationMenuPosition.value.y}px`,
}))

const activeConversationMenuTarget = computed(() => {
  const id = String(conversationMenuId.value || '').trim()
  if (!id) return null
  return appStore.conversations.find((conversation) => String(conversation?.id || '').trim() === id) || null
})

// ─── Helpers ──────────────────────────────────────────────────────────────────
function readDatasetSizeBytes(dataset) {
  const candidates = [
    dataset?.file_size,
    dataset?.file_size_bytes,
    dataset?.size_bytes,
    dataset?.bytes,
  ]
  for (const value of candidates) {
    const parsed = Number(value)
    if (Number.isFinite(parsed) && parsed >= 0) return parsed
  }
  return null
}

function formatStorage(bytes) {
  const value = Number(bytes)
  if (!Number.isFinite(value) || value < 0) return 'storage'
  if (value < 1024) return `${Math.round(value)} B`
  const units = ['KB', 'MB', 'GB', 'TB']
  let size = value / 1024
  let unitIndex = 0
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex += 1
  }
  const precision = size >= 10 ? 0 : 1
  return `${size.toFixed(precision)} ${units[unitIndex]}`
}

async function refreshWorkspaceDatasetSummary() {
  const workspaceId = String(appStore.activeWorkspaceId || '').trim()
  if (!workspaceId) {
    workspaceDatasetSummary.value = { workspaceId: '', count: 0, bytes: null, loading: false }
    return
  }

  workspaceDatasetSummary.value = {
    ...workspaceDatasetSummary.value,
    workspaceId,
    loading: true,
  }

  try {
    const response = await apiService.v1ListDatasets(workspaceId)
    if (workspaceId !== String(appStore.activeWorkspaceId || '').trim()) return
    const datasets = Array.isArray(response?.datasets) ? response.datasets : []
    let totalBytes = 0
    let hasSize = false
    for (const dataset of datasets) {
      const bytes = readDatasetSizeBytes(dataset)
      if (bytes === null) continue
      totalBytes += bytes
      hasSize = true
    }
    workspaceDatasetSummary.value = {
      workspaceId,
      count: datasets.length,
      bytes: hasSize ? totalBytes : null,
      loading: false,
    }
  } catch (_error) {
    workspaceDatasetSummary.value = {
      workspaceId,
      count: 0,
      bytes: null,
      loading: false,
    }
  }
}

function handleDatasetsChanged() {
  void refreshWorkspaceDatasetSummary()
}

// ─── Brand / collapse ─────────────────────────────────────────────────────────
function handleBrandClick() {
  appStore.setSidebarCollapsed(!appStore.isSidebarCollapsed)
}

function openSchemaEditor() {
  appStore.setActiveTab('schema-editor')
}

function openConversationTree() {
  appStore.setActiveTab('conversation-tree')
}

function conversationBadgeLabel(index, totalCount = appStore.conversations.length) {
  const total = Number(totalCount)
  const offset = Number(index)
  const ordinal = total - offset
  if (!Number.isFinite(ordinal) || ordinal <= 0) return '1'
  if (ordinal > 99) return '99+'
  return String(ordinal)
}

// ─── Profile menu ─────────────────────────────────────────────────────────────
function updateProfileMenuPosition() {
  const rect = profileMenuButtonRef.value?.getBoundingClientRect?.()
  if (!rect) return
  const menuWidth = 192
  const gap = 8
  const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 0
  const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0
  const left = Math.min(
    Math.max(rect.left, gap),
    Math.max(gap, viewportWidth - menuWidth - gap),
  )
  const fallbackHeight = 124
  const top = Math.max(gap, Math.min(rect.top - fallbackHeight - gap, viewportHeight - fallbackHeight - gap))
  profileMenuPosition.value = { left, top }
}

async function toggleProfileMenu() {
  profileMenuOpen.value = !profileMenuOpen.value
  if (profileMenuOpen.value) {
    await nextTick()
    updateProfileMenuPosition()
  }
}

function closeProfileMenu() {
  profileMenuOpen.value = false
}

function openProfileSection(tab) {
  closeProfileMenu()
  openSettings(tab)
}

// ─── Global click — close menus ───────────────────────────────────────────────
function handleGlobalClick(event) {
  const target = event?.target
  if (!(target instanceof Element)) return
  if (target.closest('[data-conversation-actions-menu]')) return
  if (profileMenuRef.value?.contains(target) || profileMenuButtonRef.value?.contains(target)) return
  closeConversationMenu()
  closeMultiConversationMenu()
  closeProfileMenu()
}

// ─── Settings open-from-outside ───────────────────────────────────────────────
function handleOpenSettingsRequest(event) {
  const tab  = String(event?.detail?.tab  || 'api').trim() || 'api'
  const step = Number(event?.detail?.step || 1)
  openSettings(tab, step)
}

// ─── Conversations ────────────────────────────────────────────────────────────
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
  conversationMenuId.value = null
  closeMultiConversationMenu()
  const target = String(id || '').trim()
  if (!target) return
  const current = String(appStore.activeConversationId || '').trim()
  try {
    if (target !== current) {
      appStore.setActiveConversationId(target)
    }
    await appStore.fetchConversationTurns({ reset: true })
  } catch (error) {
    toast.error('Conversation Error', extractApiErrorMessage(error, 'Failed to load conversation'))
  }
}

function handleConversationClick(event, conversationId, index) {
  if (event?.shiftKey) {
    selectConversationRange(index)
    return
  }
  if (event?.ctrlKey || event?.metaKey) {
    toggleConversationSelection(conversationId, index)
    return
  }
  clearConversationSelection()
  void selectConversation(conversationId)
}

function isConversationSelected(conversationId) {
  return selectedConversationIds.value.has(String(conversationId || '').trim())
}

function clearConversationSelection() {
  selectedConversationIds.value = new Set()
  lastSelectedConversationIndex.value = -1
  closeMultiConversationMenu()
}

function toggleConversationSelection(conversationId, index) {
  closeConversationMenu()
  closeMultiConversationMenu()
  const id = String(conversationId || '').trim()
  if (!id) return
  const next = new Set(selectedConversationIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selectedConversationIds.value = next
  lastSelectedConversationIndex.value = Number.isFinite(Number(index)) ? Number(index) : -1
}

function selectConversationRange(index) {
  closeConversationMenu()
  closeMultiConversationMenu()
  const endIndex = Number(index)
  if (!Number.isFinite(endIndex) || endIndex < 0) return
  const startIndex = lastSelectedConversationIndex.value >= 0 ? lastSelectedConversationIndex.value : endIndex
  const min = Math.min(startIndex, endIndex)
  const max = Math.max(startIndex, endIndex)
  const next = new Set(selectedConversationIds.value)
  for (let i = min; i <= max; i += 1) {
    const id = String(appStore.conversations[i]?.id || '').trim()
    if (id) next.add(id)
  }
  selectedConversationIds.value = next
  lastSelectedConversationIndex.value = endIndex
}

// ─── Inline title editing ─────────────────────────────────────────────────────
function startEditing(conv) {
  conversationMenuId.value = null
  editingId.value          = conv.id
  editingTitleValue.value  = conv.title || 'Untitled'
  setTimeout(() => {
    const el = editInputs.value[conv.id]
    if (el) { el.focus(); el.select() }
  }, 50)
}

function cancelEditing() {
  editingId.value         = null
  editingTitleValue.value = ''
}

async function saveTitle(id) {
  // Guard: only save for the active edit, and not if already mid-save
  if (editingId.value !== id || isSaving.value) return

  const newTitle = editingTitleValue.value.trim()
  const conv = appStore.conversations.find((c) => c.id === id)

  // No-op: empty string or unchanged
  if (!newTitle || newTitle === (conv?.title || 'Untitled')) {
    cancelEditing()
    return
  }

  // Minimum length guard — prevents saving a single stray character on accidental blur
  if (newTitle.length < 2) {
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
      if (idx !== -1) {
        appStore.conversations[idx] = { ...appStore.conversations[idx], title: updated.title }
      }
    }
  } catch (error) {
    toast.error('Rename Failed', extractApiErrorMessage(error, 'Failed to update title'))
  } finally {
    isSaving.value = false
    cancelEditing()
  }
}

// ─── Conversation context menu ────────────────────────────────────────────────
function clampMenuPosition(x, y, width = 160, height = 96) {
  const gap = 8
  const viewportWidth = typeof window === 'undefined' ? width + gap * 2 : window.innerWidth
  const viewportHeight = typeof window === 'undefined' ? height + gap * 2 : window.innerHeight
  return {
    x: Math.max(gap, Math.min(Number(x) || gap, viewportWidth - width - gap)),
    y: Math.max(gap, Math.min(Number(y) || gap, viewportHeight - height - gap)),
  }
}

function positionConversationMenuFromEvent(event) {
  const rect = event?.currentTarget?.getBoundingClientRect?.()
  if (rect) {
    return clampMenuPosition(rect.right - 128, rect.bottom + 4, 128, 88)
  }
  return clampMenuPosition(event?.clientX || 0, event?.clientY || 0, 128, 88)
}

function openSingleConversationMenu(conversationId, position) {
  const id = String(conversationId || '').trim()
  if (!id) return
  closeMultiConversationMenu()
  conversationMenuPosition.value = position
  conversationMenuId.value = id
}

function toggleConversationMenu(event, conversationId) {
  const id = String(conversationId || '').trim()
  if (!id) return
  if (conversationMenuId.value === id) {
    closeConversationMenu()
    return
  }
  openSingleConversationMenu(id, positionConversationMenuFromEvent(event))
}

function openConversationContextMenu(event, conversationId) {
  closeConversationMenu()
  const id = String(conversationId || '').trim()
  if (!id) return
  if (!selectedConversationIds.value.has(id)) {
    selectedConversationIds.value = new Set([id])
    const index = appStore.conversations.findIndex((conversation) => String(conversation?.id || '').trim() === id)
    lastSelectedConversationIndex.value = index
  }
  if (selectedConversationIds.value.size < 2) {
    closeMultiConversationMenu()
    openSingleConversationMenu(id, clampMenuPosition(event?.clientX || 0, event?.clientY || 0, 128, 88))
    return
  }
  closeConversationMenu()
  multiConversationMenu.value = {
    open: true,
    ...clampMenuPosition(event?.clientX || 0, event?.clientY || 0, 160, 48),
  }
}

function startEditingFromMenu(conv) {
  if (!conv?.id) {
    closeConversationMenu()
    return
  }
  conversationMenuId.value = null
  startEditing(conv)
}

function closeConversationMenu() {
  conversationMenuId.value = null
  conversationMenuPosition.value = { x: 0, y: 0 }
}

function closeMultiConversationMenu() {
  multiConversationMenu.value = {
    open: false,
    x: 0,
    y: 0,
  }
}

// ─── Delete conversation ──────────────────────────────────────────────────────
function confirmDeleteConversation(conversationId) {
  // Cancel any in-progress rename first — prevents blur from saving before delete fires
  cancelEditing()
  closeConversationMenu()

  const target = appStore.conversations.find((c) => c.id === conversationId)
  pendingDeleteType.value   = 'conversation'
  pendingDeleteId.value     = conversationId
  pendingDeleteIds.value    = []
  deleteDialogTitle.value   = 'Delete Conversation'
  deleteDialogMessage.value = `Are you sure you want to delete "${target?.title || 'Untitled'}"? This action cannot be undone.`
  isDeleteDialogOpen.value  = true
}

function confirmDeleteSelectedConversations() {
  cancelEditing()
  closeConversationMenu()
  closeMultiConversationMenu()

  const ids = Array.from(selectedConversationIds.value)
    .map((id) => String(id || '').trim())
    .filter(Boolean)
  if (ids.length === 0) return

  pendingDeleteType.value   = 'conversations'
  pendingDeleteId.value     = ''
  pendingDeleteIds.value    = ids
  deleteDialogTitle.value   = 'Delete Conversations'
  deleteDialogMessage.value = `Are you sure you want to delete ${ids.length} conversations? This action cannot be undone.`
  isDeleteDialogOpen.value  = true
}

function closeDeleteDialog() {
  isDeleteDialogOpen.value  = false
  pendingDeleteType.value   = ''
  pendingDeleteId.value     = ''
  pendingDeleteIds.value    = []
  deleteDialogTitle.value   = ''
  deleteDialogMessage.value = ''
}

async function confirmDelete() {
  if (!pendingDeleteId.value && pendingDeleteIds.value.length === 0) return
  try {
    if (pendingDeleteType.value === 'conversation') {
      await appStore.deleteConversationById(pendingDeleteId.value)
      clearConversationSelection()
      toast.success('Conversation Deleted', 'Conversation has been removed.')
    } else if (pendingDeleteType.value === 'conversations') {
      const ids = [...pendingDeleteIds.value]
      for (const id of ids) {
        await appStore.deleteConversationById(id)
      }
      clearConversationSelection()
      toast.success('Conversations Deleted', `${ids.length} conversations have been removed.`)
    }
    closeDeleteDialog()
  } catch (error) {
    toast.error('Delete Error', extractApiErrorMessage(error, 'Failed to delete'))
  }
}

// ─── Settings ─────────────────────────────────────────────────────────────────
function openSettings(tab = 'llm', step = 1) {
  const n = String(tab || '').trim().toLowerCase()
  if      (n === 'api'    || n === 'llm')        settingsInitialTab.value = 'llm'
  else if (n === 'workspace' || n === 'data')     settingsInitialTab.value = 'workspace'
  else if (n === 'account')                       settingsInitialTab.value = 'account'
  else if (n === 'appearance' || n === 'theme')   settingsInitialTab.value = 'appearance'
  else if (n === 'terms'  || n === 'legal')       settingsInitialTab.value = 'terms'
  else                                            settingsInitialTab.value = 'llm'

  const parsed = Number(step)
  settingsInitialStep.value = Number.isFinite(parsed) && parsed >= 1 ? Math.floor(parsed) : 1
  isSettingsOpen.value = true
}

// ─── Lifecycle ────────────────────────────────────────────────────────────────
onMounted(async () => {
  try {
    await appStore.fetchWorkspaces()
    await appStore.fetchWorkspaceDeletionJobs()
    if (appStore.activeWorkspaceId) {
      await appStore.fetchConversations()
    }
  } catch {
    // Recovery handled by parent app
  }
  window.addEventListener('sidebar-open-settings', handleOpenSettingsRequest)
  window.addEventListener('click', handleGlobalClick)
  window.addEventListener('dataset-switched', handleDatasetsChanged)
  window.addEventListener('resize', updateProfileMenuPosition)
  window.addEventListener('scroll', updateProfileMenuPosition, true)
  void refreshWorkspaceDatasetSummary()
})

onUnmounted(() => {
  window.removeEventListener('sidebar-open-settings', handleOpenSettingsRequest)
  window.removeEventListener('click', handleGlobalClick)
  window.removeEventListener('dataset-switched', handleDatasetsChanged)
  window.removeEventListener('resize', updateProfileMenuPosition)
  window.removeEventListener('scroll', updateProfileMenuPosition, true)
})

watch(() => appStore.activeWorkspaceId, async (newId) => {
  void refreshWorkspaceDatasetSummary()
  if (newId) await appStore.fetchConversations()
})

watch(() => appStore.isSidebarCollapsed, (collapsed) => {
  if (collapsed) {
    closeProfileMenu()
    closeConversationMenu()
  }
})
</script>

<style scoped>
.sidebar-root {
  min-width: 0;
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

.sidebar-initials-avatar {
  display: inline-flex;
  height: 1.5rem;
  width: 1.5rem;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: var(--color-selected-surface);
  color: var(--color-text-main);
  box-shadow: inset 0 0 0 1px var(--color-selected-border);
  font-size: 0.625rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}
</style>
