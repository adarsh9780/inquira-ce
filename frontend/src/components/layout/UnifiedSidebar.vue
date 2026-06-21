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
          class="flex items-center overflow-hidden whitespace-nowrap transition-all duration-300 ease-in-out sidebar-transition"
          :class="appStore.isSidebarCollapsed ? 'max-w-0 opacity-0 ml-0' : 'max-w-[200px] opacity-100 ml-3'"
        >
          <span class="text-[14px] font-semibold tracking-tight text-[var(--color-text-main)]">
            Inquira
          </span>
        </div>
      </button>
    </div>

    <!-- ─── Main Scroll Area ─── -->
    <div class="flex min-h-0 flex-1 flex-col overflow-hidden px-2">

      <!-- ─── Workspaces and conversations ─── -->
      <div class="flex min-h-0 flex-1 flex-col pt-3">
        <div
          class="flex h-9 w-full items-center transition-all duration-300"
          :class="appStore.isSidebarCollapsed ? 'justify-center px-0' : 'justify-start px-3'"
        >
          <button
            v-if="appStore.isSidebarCollapsed"
            type="button"
            class="flex h-6 w-6 items-center justify-center rounded-md text-[var(--color-text-muted)] hover:bg-[var(--color-text-main)]/10 hover:text-[var(--color-text-main)] focus:outline-none transition-colors"
            title="Workspace settings"
            @click.stop="appStore.openSettings('workspace')"
          >
            <FolderOpenIcon class="h-5 w-5" />
          </button>

          <template v-else>
            <span class="text-[18px] font-normal leading-none text-[var(--color-text-muted)] opacity-80">
              Projects
            </span>
          </template>
        </div>

        <div class="min-h-0 flex-1 overflow-y-auto overflow-x-hidden pb-1 custom-scrollbar">
          <div
            v-if="appStore.workspaces.length === 0"
            class="px-3 py-2 text-[12px] text-[var(--color-text-muted)] transition-opacity"
            :class="appStore.isSidebarCollapsed ? 'opacity-0' : 'opacity-100'"
          >
            Create a workspace to start.
          </div>

          <div v-else class="mt-4 space-y-6">
            <div v-for="workspace in appStore.workspaces" :key="workspace.id" class="space-y-2">
              <div class="group relative flex min-h-7 select-none items-center">
                <button
                  type="button"
                  class="flex min-w-0 flex-1 items-center text-left focus:outline-none"
                  :class="appStore.isSidebarCollapsed ? 'justify-center' : 'justify-start'"
                  :title="workspace.name || 'Untitled workspace'"
                  @click="selectWorkspace(workspace.id)"
                >
                  <div class="flex h-5 w-5 shrink-0 items-center justify-center">
                    <FolderOpenIcon class="h-[18px] w-[18px] text-[var(--color-text-main)]" />
                  </div>
                  <div
                    class="min-w-0 overflow-hidden whitespace-nowrap transition-all duration-300 ease-in-out sidebar-transition"
                    :class="appStore.isSidebarCollapsed ? 'max-w-0 opacity-0 ml-0' : 'flex-1 max-w-[210px] opacity-100 ml-2'"
                  >
                    <p class="truncate text-[18px] font-normal leading-tight text-[var(--color-text-main)]">
                      {{ workspace.name || 'Untitled workspace' }}
                    </p>
                  </div>
                </button>
              </div>

              <div v-if="!appStore.isSidebarCollapsed" class="space-y-1 pl-7">
                <div v-if="isWorkspaceConversationsLoading(workspace.id)" class="py-1 text-[14px] font-normal text-[var(--color-text-muted)]">
                  Loading conversations
                </div>
                <button
                  v-else-if="conversationsForWorkspace(workspace.id).length === 0"
                  type="button"
                  class="w-full py-1 text-left text-[14px] font-normal text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text-main)]"
                  @click="createConversation(workspace.id)"
                >
                  New conversation
                </button>
                <template v-else>
                  <div
                    v-for="conv in visibleConversationsForWorkspace(workspace.id)"
                    :key="conv.id"
                    class="group relative min-h-11 select-none rounded-lg cursor-pointer transition-colors hover:bg-[var(--color-text-main)]/5"
                    :class="[
                      'px-3 py-2',
                      appStore.activeConversationId === conv.id ? 'bg-[var(--color-selected-surface)]' : '',
                    ]"
                    :title="conv.title || 'Untitled'"
                    @click="selectConversation(workspace.id, conv.id)"
                    @contextmenu.prevent="openConversationContextMenu($event, conv.id)"
                  >
                    <div v-if="editingId === conv.id" class="flex w-full items-center gap-1" @click.stop>
                      <input
                        :ref="(el) => { if (el) editInputs[conv.id] = el }"
                        v-model="editingTitleValue"
                        class="w-full rounded border border-[var(--color-accent)] bg-[var(--color-surface)] px-2 py-1 text-[14px] text-[var(--color-text-main)] outline-none"
                        @keydown.enter.prevent="saveTitle(conv.id)"
                        @keydown.esc.prevent="cancelEditing"
                        @blur="saveTitle(conv.id)"
                      />
                    </div>

                    <template v-else>
                      <div class="min-w-0 pr-6">
                        <p
                          class="truncate text-[15px] leading-snug"
                          :class="appStore.activeConversationId === conv.id
                            ? 'font-normal text-[var(--color-text-main)]'
                            : 'text-[var(--color-text-muted)] group-hover:text-[var(--color-text-main)]'"
                          :title="conv.title || 'Untitled'"
                        >
                          {{ conv.title || 'Untitled' }}
                        </p>
                        <p class="mt-0.5 truncate text-[12px] leading-none text-[var(--color-text-muted)]">
                          {{ formatConversationTimestamp(conv) }}
                        </p>
                      </div>

                      <div class="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 transition-opacity group-hover:opacity-100">
                        <button
                          type="button"
                          class="flex h-6 w-6 items-center justify-center rounded-md bg-[var(--color-panel)] text-[var(--color-text-muted)] shadow-sm hover:bg-[var(--color-surface)] hover:text-[var(--color-text-main)] focus:outline-none"
                          title="Conversation actions"
                          @click.stop="toggleConversationMenu($event, conv.id)"
                        >
                          <EllipsisHorizontalIcon class="h-4 w-4" />
                        </button>
                      </div>
                    </template>
                  </div>
                  <button
                    v-if="hasHiddenConversations(workspace.id)"
                    type="button"
                    class="py-1 text-left text-[14px] font-normal text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text-main)]"
                    @click="showMoreConversations(workspace.id)"
                  >
                    Show more
                  </button>
                </template>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ─── Workspace Views ─── -->
      <nav class="flex-none pb-2 pt-2">
        <div class="flex flex-col space-y-0.5">
          <div class="relative w-full">
            <div
              v-if="appStore.activeTab === 'schema-editor' && !appStore.isSidebarCollapsed"
              class="absolute left-0 top-1/2 -translate-y-1/2 h-[18px] w-[4px] rounded-r-full bg-[var(--color-accent)] transition-all duration-300"
            />
            <button
              type="button"
              class="flex w-full items-center rounded-lg py-2 text-left transition-colors hover:bg-[var(--color-text-main)]/5 focus:outline-none"
              :class="[
                appStore.isSidebarCollapsed ? 'justify-center px-0' : 'justify-start px-3',
                appStore.activeTab === 'schema-editor' ? 'bg-[var(--color-selected-surface)] text-[var(--color-text-main)]' : 'text-[var(--color-text-muted)]',
              ]"
              :title="shortcutTooltip('schema', appStore.isSidebarCollapsed ? 'Open schema editor' : 'Schema editor')"
              @click="openSchemaEditor"
            >
              <div class="flex h-6 w-6 shrink-0 items-center justify-center">
                <CircleStackIcon class="h-5 w-5" :class="appStore.activeTab === 'schema-editor' ? 'text-[var(--color-accent)]' : 'text-[var(--color-text-main)]'" />
              </div>
              <div
                class="overflow-hidden whitespace-nowrap transition-all duration-300 ease-in-out sidebar-transition"
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
          </div>

          <div class="relative w-full">
            <div
              v-if="appStore.activeTab === 'conversation-tree' && !appStore.isSidebarCollapsed"
              class="absolute left-0 top-1/2 -translate-y-1/2 h-[18px] w-[4px] rounded-r-full bg-[var(--color-accent)] transition-all duration-300"
            />
            <button
              type="button"
              class="flex w-full items-center rounded-lg py-2 text-left transition-colors hover:bg-[var(--color-text-main)]/5 focus:outline-none"
              :class="[
                appStore.isSidebarCollapsed ? 'justify-center px-0' : 'justify-start px-3',
                appStore.activeTab === 'conversation-tree' ? 'bg-[var(--color-selected-surface)] text-[var(--color-text-main)]' : 'text-[var(--color-text-muted)]',
              ]"
              :title="shortcutTooltip('conversation-tree', appStore.isSidebarCollapsed ? 'Open conversation tree' : 'Conversation tree')"
              @click="openConversationTree"
            >
              <div class="flex h-6 w-6 shrink-0 items-center justify-center">
                <ShareIcon class="h-5 w-5" :class="appStore.activeTab === 'conversation-tree' ? 'text-[var(--color-accent)]' : 'text-[var(--color-text-main)]'" />
              </div>
              <div
                class="overflow-hidden whitespace-nowrap transition-all duration-300 ease-in-out sidebar-transition"
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
              class="overflow-hidden whitespace-nowrap transition-all duration-300 ease-in-out sidebar-transition"
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
            @click="appStore.openSettings('llm')"
          >
            <div class="flex h-6 w-6 shrink-0 items-center justify-center">
              <Cog6ToothIcon class="h-5 w-5" />
            </div>
            <div
              class="overflow-hidden whitespace-nowrap transition-all duration-300 ease-in-out sidebar-transition"
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
                class="overflow-hidden whitespace-nowrap transition-all duration-300 ease-in-out sidebar-transition"
                :class="appStore.isSidebarCollapsed ? 'max-w-0 opacity-0 ml-0' : 'max-w-[200px] opacity-100 ml-3'"
              >
                <span class="text-[13px] font-medium">{{ profileDisplayName }}</span>
              </div>
            </button>

          </div>

        </div>
      </nav>
    </div>


    <ConfirmationModal
      :is-open="isDeleteDialogOpen"
      :title="deleteDialogTitle"
      :message="deleteDialogMessage"
      confirm-text="Delete"
      cancel-text="Cancel"
      @close="closeDeleteDialog"
      @confirm="confirmDelete"
    />
    <TermsModal
      :is-open="isTermsOpen"
      @close="isTermsOpen = false"
    />
    <KeyboardShortcutsModal
      :is-open="appStore.isKeyboardShortcutsOpen"
      @close="appStore.closeKeyboardShortcuts()"
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
        <button
          type="button"
          class="w-full px-3 py-2 text-left text-[13px] font-medium text-[var(--color-text-main)] hover:bg-[var(--color-panel-muted)] transition-colors"
          :title="shortcutTooltip('keyboard-shortcuts', 'Keyboard Shortcuts')"
          @click="openKeyboardShortcuts"
        >
          Keyboard Shortcuts
        </button>
        <div class="h-px bg-[var(--color-border)] my-1 opacity-60" />
        <template v-if="false">
          <button
            type="button"
            class="w-full px-3 py-2 text-left text-[13px] font-medium text-[var(--color-text-main)] hover:bg-[var(--color-panel-muted)] transition-colors"
            @click="openProfileSection('terms')"
          >
            Legal &amp; Terms
          </button>
        </template>
        <button
          type="button"
          class="w-full px-3 py-2 text-left text-[13px] font-medium text-[var(--color-text-main)] hover:bg-[var(--color-panel-muted)] transition-colors"
          @click="openTermsModal"
        >
          Terms &amp; Conditions
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
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { useAppStore } from '../../stores/appStore'
import { useAuthStore } from '../../stores/authStore'
import { toast } from '../../composables/useToast'
import { extractApiErrorMessage } from '../../utils/apiError'
import { formatTimestamp } from '../../utils/dateUtils'
import { shortcutTitle } from '../../utils/keyboardShortcuts'
import ConfirmationModal from '../modals/ConfirmationModal.vue'
import KeyboardShortcutsModal from '../modals/KeyboardShortcutsModal.vue'
import TermsModal from '../modals/TermsModal.vue'
import logo from '../../assets/favicon.svg'
import apiService from '../../services/apiService'

import {
  FolderOpenIcon,
  PlusIcon,
  EllipsisHorizontalIcon,
  CircleStackIcon,
  ShareIcon,
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

const conversationMenuId       = ref(null)
const conversationMenuPosition = ref({ x: 0, y: 0 })
const profileMenuOpen      = ref(false)
const profileMenuRef       = ref(null)
const profileMenuButtonRef = ref(null)
const profileMenuPosition  = ref({ left: 0, top: 0 })
const sidebarConversationsByWorkspace = ref({})
const loadingConversationsByWorkspace = ref({})
const visibleConversationCountByWorkspace = ref({})
const DEFAULT_VISIBLE_CONVERSATION_COUNT = 5

// ─── Settings Modal ───────────────────────────────────────────────────────────
const isTermsOpen         = ref(false)

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

const conversationMenuStyle = computed(() => ({
  left: `${conversationMenuPosition.value.x}px`,
  top: `${conversationMenuPosition.value.y}px`,
}))

const activeConversationMenuTarget = computed(() => {
  const id = String(conversationMenuId.value || '').trim()
  if (!id) return null
  return findSidebarConversation(id)
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

function conversationsForWorkspace(workspaceId) {
  const normalizedWorkspaceId = String(workspaceId || '').trim()
  if (!normalizedWorkspaceId) return []
  if (normalizedWorkspaceId === String(appStore.activeWorkspaceId || '').trim()) {
    return Array.isArray(appStore.conversations) ? appStore.conversations : []
  }
  return Array.isArray(sidebarConversationsByWorkspace.value?.[normalizedWorkspaceId])
    ? sidebarConversationsByWorkspace.value[normalizedWorkspaceId]
    : []
}

function visibleConversationCount(workspaceId) {
  const normalizedWorkspaceId = String(workspaceId || '').trim()
  const value = Number(visibleConversationCountByWorkspace.value?.[normalizedWorkspaceId])
  return Number.isFinite(value) && value > 0
    ? Math.max(DEFAULT_VISIBLE_CONVERSATION_COUNT, Math.floor(value))
    : DEFAULT_VISIBLE_CONVERSATION_COUNT
}

function visibleConversationsForWorkspace(workspaceId) {
  return conversationsForWorkspace(workspaceId).slice(0, visibleConversationCount(workspaceId))
}

function hasHiddenConversations(workspaceId) {
  return conversationsForWorkspace(workspaceId).length > visibleConversationCount(workspaceId)
}

function showMoreConversations(workspaceId) {
  const normalizedWorkspaceId = String(workspaceId || '').trim()
  if (!normalizedWorkspaceId) return
  visibleConversationCountByWorkspace.value = {
    ...visibleConversationCountByWorkspace.value,
    [normalizedWorkspaceId]: visibleConversationCount(normalizedWorkspaceId) + DEFAULT_VISIBLE_CONVERSATION_COUNT,
  }
}

function updateSidebarConversationCache(workspaceId, conversations) {
  const normalizedWorkspaceId = String(workspaceId || '').trim()
  if (!normalizedWorkspaceId) return
  sidebarConversationsByWorkspace.value = {
    ...sidebarConversationsByWorkspace.value,
    [normalizedWorkspaceId]: Array.isArray(conversations) ? conversations : [],
  }
}

function findSidebarConversation(conversationId) {
  const normalizedConversationId = String(conversationId || '').trim()
  if (!normalizedConversationId) return null
  const activeMatch = appStore.conversations.find((conversation) => String(conversation?.id || '').trim() === normalizedConversationId)
  if (activeMatch) return activeMatch
  for (const conversations of Object.values(sidebarConversationsByWorkspace.value || {})) {
    const match = Array.isArray(conversations)
      ? conversations.find((conversation) => String(conversation?.id || '').trim() === normalizedConversationId)
      : null
    if (match) return match
  }
  return null
}

function removeConversationFromSidebarCache(conversationId) {
  const normalizedConversationId = String(conversationId || '').trim()
  if (!normalizedConversationId) return
  const nextCache = {}
  for (const [workspaceId, conversations] of Object.entries(sidebarConversationsByWorkspace.value || {})) {
    nextCache[workspaceId] = Array.isArray(conversations)
      ? conversations.filter((conversation) => String(conversation?.id || '').trim() !== normalizedConversationId)
      : []
  }
  sidebarConversationsByWorkspace.value = nextCache
}

function isWorkspaceConversationsLoading(workspaceId) {
  return Boolean(loadingConversationsByWorkspace.value?.[String(workspaceId || '').trim()])
}

async function loadSidebarConversations(workspaceId, { force = false } = {}) {
  const normalizedWorkspaceId = String(workspaceId || '').trim()
  if (!normalizedWorkspaceId) return []
  if (!force && sidebarConversationsByWorkspace.value?.[normalizedWorkspaceId]) {
    return sidebarConversationsByWorkspace.value[normalizedWorkspaceId]
  }
  loadingConversationsByWorkspace.value = {
    ...loadingConversationsByWorkspace.value,
    [normalizedWorkspaceId]: true,
  }
  try {
    const response = await apiService.v1ListConversations(normalizedWorkspaceId, 50)
    const conversations = Array.isArray(response?.conversations) ? response.conversations : []
    updateSidebarConversationCache(normalizedWorkspaceId, conversations)
    return conversations
  } catch (_error) {
    updateSidebarConversationCache(normalizedWorkspaceId, [])
    return []
  } finally {
    loadingConversationsByWorkspace.value = {
      ...loadingConversationsByWorkspace.value,
      [normalizedWorkspaceId]: false,
    }
  }
}

async function loadAllSidebarConversations({ force = false } = {}) {
  const workspaces = Array.isArray(appStore.workspaces) ? appStore.workspaces : []
  await Promise.all(
    workspaces
      .map((workspace) => String(workspace?.id || '').trim())
      .filter(Boolean)
      .map((workspaceId) => loadSidebarConversations(workspaceId, { force })),
  )
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

function formatConversationTimestamp(conversation) {
  if (appStore.isConversationRunning(conversation?.id)) return 'Running...'
  return formatTimestamp(conversation?.last_turn_at || conversation?.updated_at || conversation?.created_at)
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
  const fallbackHeight = 160
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
  appStore.openSettings(tab)
}

function openTermsModal() {
  closeProfileMenu()
  isTermsOpen.value = true
}

function openKeyboardShortcuts() {
  closeProfileMenu()
  appStore.openKeyboardShortcuts()
}

function shortcutTooltip(shortcutId, fallback) {
  const platform = typeof navigator !== 'undefined' ? navigator.platform : ''
  return shortcutTitle(shortcutId, fallback, platform)
}

// ─── Global click — close menus ───────────────────────────────────────────────
function handleGlobalClick(event) {
  const target = event?.target
  if (!(target instanceof Element)) return
  if (target.closest('[data-conversation-actions-menu]')) return
  if (profileMenuRef.value?.contains(target) || profileMenuButtonRef.value?.contains(target)) return
  closeConversationMenu()
  closeProfileMenu()
}

// ─── Settings open-from-outside ───────────────────────────────────────────────
function handleOpenSettingsRequest(event) {
  const tab  = String(event?.detail?.tab  || 'api').trim() || 'api'
  appStore.openSettings(tab)
}

// ─── Conversations ────────────────────────────────────────────────────────────
async function selectWorkspace(workspaceId) {
  const normalizedWorkspaceId = String(workspaceId || '').trim()
  if (!normalizedWorkspaceId) return
  try {
    if (normalizedWorkspaceId !== String(appStore.activeWorkspaceId || '').trim()) {
      await appStore.activateWorkspace(normalizedWorkspaceId)
    }
    await appStore.fetchConversations()
    updateSidebarConversationCache(normalizedWorkspaceId, appStore.conversations)
    await loadSidebarConversations(normalizedWorkspaceId, { force: true })
  } catch (error) {
    toast.error('Workspace Error', extractApiErrorMessage(error, 'Failed to open workspace'))
  }
}

async function createConversation(workspaceId = appStore.activeWorkspaceId) {
  const normalizedWorkspaceId = String(workspaceId || '').trim()
  try {
    if (normalizedWorkspaceId && normalizedWorkspaceId !== String(appStore.activeWorkspaceId || '').trim()) {
      await appStore.activateWorkspace(normalizedWorkspaceId)
      await appStore.fetchConversations()
    }
    const conversation = await appStore.createConversation()
    updateSidebarConversationCache(String(appStore.activeWorkspaceId || '').trim(), appStore.conversations)
    if (conversation?.id) {
      appStore.setActiveConversationId(conversation.id)
      await appStore.fetchConversationTurns({ reset: true })
    }
  } catch (error) {
    toast.error('Conversation Error', extractApiErrorMessage(error, 'Failed to create conversation'))
  }
}

async function selectConversation(workspaceId, id) {
  closeConversationMenu()
  const normalizedWorkspaceId = String(workspaceId || '').trim()
  const target = String(id || '').trim()
  if (!target) return
  const current = String(appStore.activeConversationId || '').trim()
  try {
    if (normalizedWorkspaceId && normalizedWorkspaceId !== String(appStore.activeWorkspaceId || '').trim()) {
      await appStore.activateWorkspace(normalizedWorkspaceId)
      await appStore.fetchConversations()
      updateSidebarConversationCache(normalizedWorkspaceId, appStore.conversations)
    }
    if (target !== current) {
      appStore.setActiveConversationId(target)
    } else {
      appStore.setWorkspacePane('chat')
      appStore.setActiveTab('workspace')
    }
    await appStore.fetchConversationTurns({ reset: true, preferLatest: true })
  } catch (error) {
    toast.error('Conversation Error', extractApiErrorMessage(error, 'Failed to load conversation'))
  }
}

// ─── Inline title editing ─────────────────────────────────────────────────────
function startEditing(conv) {
  closeConversationMenu()
  editingId.value         = conv.id
  editingTitleValue.value = conv.title || 'Untitled'
  setTimeout(() => {
    const el = editInputs.value[conv.id]
    if (el) {
      el.focus()
      el.select()
    }
  }, 50)
}

function cancelEditing() {
  editingId.value         = null
  editingTitleValue.value = ''
}

async function saveTitle(id) {
  if (editingId.value !== id || isSaving.value) return

  const newTitle = editingTitleValue.value.trim()
  const conv = findSidebarConversation(id)

  if (!newTitle || newTitle === (conv?.title || 'Untitled')) {
    cancelEditing()
    return
  }

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
      const idx = appStore.conversations.findIndex((conversation) => conversation.id === id)
      if (idx !== -1) {
        appStore.conversations[idx] = { ...appStore.conversations[idx], title: updated.title }
      }
      for (const [workspaceId, conversations] of Object.entries(sidebarConversationsByWorkspace.value || {})) {
        const cachedIndex = Array.isArray(conversations)
          ? conversations.findIndex((conversation) => String(conversation?.id || '').trim() === id)
          : -1
        if (cachedIndex === -1) continue
        const nextConversations = [...conversations]
        nextConversations[cachedIndex] = { ...nextConversations[cachedIndex], title: updated.title }
        updateSidebarConversationCache(workspaceId, nextConversations)
        break
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
  openSingleConversationMenu(id, clampMenuPosition(event?.clientX || 0, event?.clientY || 0, 128, 88))
}

function startEditingFromMenu(conv) {
  if (!conv?.id) {
    closeConversationMenu()
    return
  }
  startEditing(conv)
}

function closeConversationMenu() {
  conversationMenuId.value = null
  conversationMenuPosition.value = { x: 0, y: 0 }
}

// ─── Delete conversation ──────────────────────────────────────────────────────
function confirmDeleteConversation(conversationId) {
  cancelEditing()
  closeConversationMenu()

  const target = findSidebarConversation(conversationId)
  pendingDeleteType.value   = 'conversation'
  pendingDeleteId.value     = conversationId
  pendingDeleteIds.value    = []
  deleteDialogTitle.value   = 'Delete Conversation'
  deleteDialogMessage.value = `Are you sure you want to delete "${target?.title || 'Untitled'}"? This action cannot be undone.`
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
      removeConversationFromSidebarCache(pendingDeleteId.value)
      toast.success('Conversation Deleted', 'Conversation has been removed.')
    } else if (pendingDeleteType.value === 'conversations') {
      const ids = [...pendingDeleteIds.value]
      for (const id of ids) {
        await appStore.deleteConversationById(id)
        removeConversationFromSidebarCache(id)
      }
      toast.success('Conversations Deleted', `${ids.length} conversations have been removed.`)
    }
    closeDeleteDialog()
  } catch (error) {
    toast.error('Delete Error', extractApiErrorMessage(error, 'Failed to delete'))
  }
}



// ─── Lifecycle ────────────────────────────────────────────────────────────────
onMounted(async () => {
  try {
    await appStore.fetchWorkspaces()
    await appStore.fetchWorkspaceDeletionJobs()
    if (appStore.activeWorkspaceId) {
      await appStore.fetchConversations()
      updateSidebarConversationCache(appStore.activeWorkspaceId, appStore.conversations)
    }
    await loadAllSidebarConversations()
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
  if (newId) {
    await appStore.fetchConversations()
    updateSidebarConversationCache(newId, appStore.conversations)
  }
})

watch(() => appStore.workspaces.map((workspace) => workspace.id).join('|'), async () => {
  await loadAllSidebarConversations()
})

watch(() => appStore.conversations, (items) => {
  const workspaceId = String(appStore.activeWorkspaceId || '').trim()
  if (!workspaceId) return
  updateSidebarConversationCache(workspaceId, Array.isArray(items) ? items : [])
}, { deep: true })

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
  transition: background-color var(--motion-duration-standard) var(--motion-ease-standard),
              transform var(--motion-duration-standard) var(--motion-ease-standard);
}

.sidebar-initials-avatar:hover {
  transform: scale(1.05);
}

.sidebar-transition {
  transition: all var(--motion-duration-slow) var(--motion-ease-emphasized) !important;
}
</style>
