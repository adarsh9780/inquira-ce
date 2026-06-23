<template>
  <div
    class="relative z-40 flex h-full w-full min-h-0 min-w-0 flex-col overflow-hidden sidebar-root"
  >
    <!-- ─── Brand / Collapse Toggle ─── -->
    <div
      class="sidebar-brand-row justify-between px-4"
    >
      <button
        class="sidebar-brand-button justify-start"
        :title="appStore.isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"
        @click="handleBrandClick"
      >
        <div class="flex h-7 w-7 shrink-0 items-center justify-center">
          <img :src="logo" alt="Inquira" class="h-full w-full rounded-md" />
        </div>
        <div
          class="flex items-center overflow-hidden whitespace-nowrap transition-all duration-300 ease-in-out sidebar-transition"
          :class="appStore.isSidebarCollapsed ? 'max-w-0 opacity-0 ml-0' : 'max-w-[160px] opacity-100 ml-2.5'"
        >
          <span class="text-[13px] font-semibold text-[var(--color-text-main)]">
            Inquira
          </span>
        </div>
      </button>
      <button
        v-if="!appStore.isSidebarCollapsed"
        type="button"
        class="sidebar-icon-button"
        title="Collapse sidebar"
        @click="handleBrandClick"
      >
        <ChevronDoubleLeftIcon class="h-4 w-4" />
      </button>
    </div>

    <!-- ─── Main Scroll Area ─── -->
    <div class="flex min-h-0 flex-1 flex-col overflow-hidden px-2">
      <!-- ─── Primary Actions ─── -->
      <SidebarPrimaryNav>
        <button
          type="button"
          class="sidebar-nav-row sidebar-primary-row justify-start px-2.5"
          title="New conversation"
          @click="createConversation()"
        >
          <span class="sidebar-row-icon">
            <PencilSquareIcon class="h-5 w-5" />
          </span>
          <span
            class="sidebar-row-label"
            :class="appStore.isSidebarCollapsed ? 'max-w-0 opacity-0 ml-0' : 'max-w-[176px] opacity-100 ml-2.5'"
          >
            New conversation
          </span>
        </button>

        <button
          type="button"
          class="sidebar-nav-row sidebar-primary-row justify-start px-2.5"
          :title="sidebarSearchOpen ? 'Close search' : 'Search conversations'"
          @click="toggleSidebarSearch"
        >
          <span class="sidebar-row-icon">
            <MagnifyingGlassIcon v-if="!sidebarSearchOpen" class="h-5 w-5" />
            <XMarkIcon v-else class="h-5 w-5" />
          </span>
          <span
            class="sidebar-row-label"
            :class="appStore.isSidebarCollapsed ? 'max-w-0 opacity-0 ml-0' : 'max-w-[176px] opacity-100 ml-2.5'"
          >
            {{ sidebarSearchOpen ? 'Close search' : 'Search' }}
          </span>
        </button>

        <div v-if="sidebarSearchOpen && !appStore.isSidebarCollapsed" class="px-1.5 pb-1 pt-1">
          <input
            v-model="sidebarSearchQuery"
            class="sidebar-search-input"
            type="search"
            placeholder="Search conversations"
            aria-label="Search conversations"
          />
        </div>

        <button
          type="button"
          class="sidebar-nav-row justify-start px-2.5"
          :class="[
            appStore.activeTab === 'schema-editor' ? 'sidebar-nav-row-active' : '',
          ]"
          :title="shortcutTooltip('schema', appStore.isSidebarCollapsed ? 'Open schema editor' : 'Schema editor')"
          @click="openSchemaEditor"
        >
          <span class="sidebar-row-icon">
            <CircleStackIcon class="h-5 w-5" :class="appStore.activeTab === 'schema-editor' ? 'text-[var(--color-accent)]' : ''" />
          </span>
          <span
            class="sidebar-row-label"
            :class="appStore.isSidebarCollapsed ? 'max-w-0 opacity-0 ml-0' : 'max-w-[176px] opacity-100 ml-2.5'"
          >
            Schema
          </span>
        </button>

        <button
          type="button"
          class="sidebar-nav-row justify-start px-2.5"
          :class="[
            appStore.activeTab === 'conversation-tree' ? 'sidebar-nav-row-active' : '',
          ]"
          :title="shortcutTooltip('conversation-tree', appStore.isSidebarCollapsed ? 'Open conversation tree' : 'Conversation tree')"
          @click="openConversationTree"
        >
          <span class="sidebar-row-icon">
            <ShareIcon class="h-5 w-5" :class="appStore.activeTab === 'conversation-tree' ? 'text-[var(--color-accent)]' : ''" />
          </span>
          <span
            class="sidebar-row-label"
            :class="appStore.isSidebarCollapsed ? 'max-w-0 opacity-0 ml-0' : 'max-w-[176px] opacity-100 ml-2.5'"
          >
            Conversation Tree
          </span>
        </button>
      </SidebarPrimaryNav>

      <!-- ─── Workspaces and conversations ─── -->
      <SidebarWorkspaceConversations>
        <div
          class="flex w-full items-center overflow-hidden transition-all duration-300"
          :class="appStore.isSidebarCollapsed ? 'h-0 px-0 opacity-0' : 'h-7 justify-between px-2.5 opacity-100'"
        >
          <template v-if="!appStore.isSidebarCollapsed">
            <span class="sidebar-section-label">
              Projects
            </span>
            <button
              type="button"
              class="sidebar-icon-button"
              title="Workspace settings"
              @click.stop="appStore.openSettings('workspace')"
            >
              <Cog6ToothIcon class="h-4 w-4" />
            </button>
          </template>
        </div>

        <div class="min-h-0 flex-1 overflow-y-auto overflow-x-hidden pb-1 custom-scrollbar">
          <div
            v-if="appStore.workspaces.length === 0"
            class="px-2.5 py-2 text-[12px] text-[var(--color-text-muted)] transition-opacity"
            :class="appStore.isSidebarCollapsed ? 'opacity-0' : 'opacity-100'"
          >
            Create a workspace to start.
          </div>

          <div v-else-if="filteredSidebarWorkspaces.length === 0 && !appStore.isSidebarCollapsed" class="px-2.5 py-3 text-[12px] text-[var(--color-text-muted)]">
            No matching conversations.
          </div>

          <div v-else class="mt-2 space-y-4">
            <div v-for="workspace in filteredSidebarWorkspaces" :key="workspace.id" class="space-y-1">
              <div class="group relative flex min-h-8 select-none items-center">
                <button
                  type="button"
                  class="sidebar-workspace-row justify-start px-2.5"
                  :class="[
                    appStore.activeWorkspaceId === workspace.id ? 'sidebar-workspace-row-active' : '',
                  ]"
                  :title="workspace.name || 'Untitled workspace'"
                  @click="selectWorkspace(workspace.id)"
                >
                  <span class="sidebar-row-icon">
                    <FolderOpenIcon class="h-[18px] w-[18px]" />
                  </span>
                  <div
                    class="min-w-0 overflow-hidden whitespace-nowrap transition-all duration-300 ease-in-out sidebar-transition"
                    :class="appStore.isSidebarCollapsed ? 'max-w-0 opacity-0 ml-0' : 'flex-1 max-w-[180px] opacity-100 ml-2.5'"
                  >
                    <p class="truncate text-[13px] font-semibold leading-tight text-[var(--color-text-main)]">
                      {{ workspace.name || 'Untitled workspace' }}
                    </p>
                  </div>
                </button>
              </div>

              <div v-if="!appStore.isSidebarCollapsed" class="space-y-0.5 pl-7 pr-1">
                <div v-if="isWorkspaceConversationsLoading(workspace.id)" class="px-2 py-1.5 text-[12px] font-medium text-[var(--color-text-muted)]">
                  Loading conversations
                </div>
                <button
                  v-else-if="visibleConversationsForSidebar(workspace).length === 0"
                  type="button"
                  class="w-full rounded-md px-2 py-1.5 text-left text-[12px] font-medium text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-text-main)]/5 hover:text-[var(--color-text-main)]"
                  @click="createConversation(workspace.id)"
                >
                  New conversation
                </button>
                <template v-else>
                  <SidebarConversationRow
                    v-for="conv in visibleConversationsForSidebar(workspace)"
                    :key="conv.id"
                    v-model:editing-title-value="editingTitleValue"
                    :conversation="conv"
                    :active="appStore.activeConversationId === conv.id"
                    :is-editing="editingId === conv.id"
                    :compact-timestamp="formatConversationTimestamp(conv)"
                    :menu-open="conversationMenuId === conv.id"
                    @select="selectConversation(workspace.id, conv.id)"
                    @contextmenu="openConversationContextMenu($event, conv.id)"
                    @toggle-menu="toggleConversationMenu($event, conv.id)"
                    @save-title="saveTitle(conv.id)"
                    @cancel-edit="cancelEditing"
                  />
                  <button
                    v-if="hasHiddenConversationsForSidebar(workspace)"
                    type="button"
                    class="rounded-md px-2 py-1.5 text-left text-[12px] font-medium text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-text-main)]/5 hover:text-[var(--color-text-main)]"
                    @click="showMoreConversations(workspace.id)"
                  >
                    Show more
                  </button>
                </template>
              </div>
            </div>
          </div>
        </div>
      </SidebarWorkspaceConversations>

      <!-- ─── Footer Navigation ─── -->
      <SidebarFooter>
        <div class="mx-1 mb-2 h-px bg-[var(--color-border)] opacity-70" />
        <div class="flex flex-col space-y-0.5">
          <!-- Settings -->
          <button
            type="button"
            class="sidebar-nav-row justify-start px-2.5"
            title="Settings"
            @click="appStore.openSettings('llm')"
          >
            <span class="sidebar-row-icon">
              <Cog6ToothIcon class="h-5 w-5" />
            </span>
            <span
              class="sidebar-row-label"
              :class="appStore.isSidebarCollapsed ? 'max-w-0 opacity-0 ml-0' : 'max-w-[176px] opacity-100 ml-2.5'"
            >
              Settings
            </span>
          </button>

          <!-- Profile -->
          <div class="relative">
            <button
              ref="profileMenuButtonRef"
              type="button"
              class="sidebar-nav-row justify-start px-2.5"
              :class="[
                profileMenuOpen
                  ? 'sidebar-nav-row-active'
                  : '',
              ]"
              title="Profile Settings"
              @click="toggleProfileMenu"
            >
              <span class="sidebar-row-icon">
                <span class="sidebar-initials-avatar">
                  {{ profileInitials }}
                </span>
              </span>
              <span
                class="sidebar-row-label"
                :class="appStore.isSidebarCollapsed ? 'max-w-0 opacity-0 ml-0' : 'max-w-[176px] opacity-100 ml-2.5'"
              >
                {{ profileDisplayName }}
              </span>
            </button>

          </div>

        </div>
      </SidebarFooter>
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
        <button
          type="button"
          class="w-full px-3 py-2 text-left text-[13px] font-medium text-[var(--color-text-main)] hover:bg-[var(--color-panel-muted)] transition-colors"
          @click="openTermsModal"
        >
          Terms &amp; Conditions
        </button>
      </div>
    </Teleport>
    <SidebarConversationActionsMenu
      :is-open="Boolean(conversationMenuId)"
      :position="conversationMenuPosition"
      :exact-date="activeConversationMenuExactDate"
      @rename="startEditingFromMenu(activeConversationMenuTarget)"
      @delete="confirmDeleteConversation(conversationMenuId)"
      @close="closeConversationMenu"
    />
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { useAppStore } from '../../stores/appStore'
import { useAuthStore } from '../../stores/authStore'
import { toast } from '../../composables/useToast'
import { extractApiErrorMessage } from '../../utils/apiError'
import { formatCompactRelativeTimestamp, formatExactTimestamp } from '../../utils/dateUtils'
import { shortcutTitle } from '../../utils/keyboardShortcuts'
import ConfirmationModal from '../modals/ConfirmationModal.vue'
import KeyboardShortcutsModal from '../modals/KeyboardShortcutsModal.vue'
import TermsModal from '../modals/TermsModal.vue'
import SidebarConversationActionsMenu from './sidebar/SidebarConversationActionsMenu.vue'
import SidebarConversationRow from './sidebar/SidebarConversationRow.vue'
import SidebarFooter from './sidebar/SidebarFooter.vue'
import SidebarPrimaryNav from './sidebar/SidebarPrimaryNav.vue'
import SidebarWorkspaceConversations from './sidebar/SidebarWorkspaceConversations.vue'
import logo from '../../assets/favicon.svg'
import apiService from '../../services/apiService'
import { sidebarConversationPageSize, useSidebarConversations } from '../../composables/useSidebarConversations'

import {
  FolderOpenIcon,
  CircleStackIcon,
  ShareIcon,
  Cog6ToothIcon,
  ChevronDoubleLeftIcon,
  MagnifyingGlassIcon,
  PencilSquareIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'

// ─── Store ───────────────────────────────────────────────────────────────────
const appStore = useAppStore()
const authStore = useAuthStore()

// ─── UI State ────────────────────────────────────────────────────────────────
const editingId         = ref(null)
const editingTitleValue = ref('')
const isSaving          = ref(false)

const conversationMenuId       = ref(null)
const conversationMenuPosition = ref({ x: 0, y: 0 })
const profileMenuOpen      = ref(false)
const profileMenuRef       = ref(null)
const profileMenuButtonRef = ref(null)
const profileMenuPosition  = ref({ left: 0, top: 0 })
const sidebarSearchOpen = ref(false)
const sidebarSearchQuery = ref('')
const sidebarConversationsByWorkspace = ref({})
const loadingConversationsByWorkspace = ref({})
const visibleConversationCountByWorkspace = ref({})
const DEFAULT_VISIBLE_CONVERSATION_COUNT = sidebarConversationPageSize
useSidebarConversations()

// ─── Settings Modal ───────────────────────────────────────────────────────────
const isTermsOpen         = ref(false)

// ─── Delete Dialog ────────────────────────────────────────────────────────────
const isDeleteDialogOpen  = ref(false)
const deleteDialogTitle   = ref('')
const deleteDialogMessage = ref('')
const pendingDeleteId     = ref('')

// ─── Computed ─────────────────────────────────────────────────────────────────
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

const activeConversationMenuTarget = computed(() => {
  const id = String(conversationMenuId.value || '').trim()
  if (!id) return null
  return findSidebarConversation(id)
})

const activeConversationMenuExactDate = computed(() => (
  formatExactTimestamp(conversationTimestampValue(activeConversationMenuTarget.value))
))

const normalizedSidebarSearchQuery = computed(() => (
  String(sidebarSearchQuery.value || '').trim().toLowerCase()
))

const filteredSidebarWorkspaces = computed(() => {
  const workspaces = Array.isArray(appStore.workspaces) ? appStore.workspaces : []
  const query = normalizedSidebarSearchQuery.value
  if (!query) return workspaces
  return workspaces.filter((workspace) => workspaceMatchesSidebarSearch(workspace, query))
})

// ─── Helpers ──────────────────────────────────────────────────────────────────
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

function conversationMatchesSidebarSearch(conversation, query = normalizedSidebarSearchQuery.value) {
  const normalizedQuery = String(query || '').trim().toLowerCase()
  if (!normalizedQuery) return true
  return String(conversation?.title || 'Untitled').toLowerCase().includes(normalizedQuery)
}

function workspaceMatchesSidebarSearch(workspace, query = normalizedSidebarSearchQuery.value) {
  const normalizedQuery = String(query || '').trim().toLowerCase()
  if (!normalizedQuery) return true
  const workspaceName = String(workspace?.name || 'Untitled workspace').toLowerCase()
  if (workspaceName.includes(normalizedQuery)) return true
  return conversationsForWorkspace(workspace?.id).some((conversation) => (
    conversationMatchesSidebarSearch(conversation, normalizedQuery)
  ))
}

function visibleConversationsForSidebar(workspace) {
  const workspaceId = String(workspace?.id || '').trim()
  const conversations = conversationsForWorkspace(workspaceId)
  const query = normalizedSidebarSearchQuery.value
  if (!query) return conversations.slice(0, visibleConversationCount(workspaceId))
  const workspaceName = String(workspace?.name || 'Untitled workspace').toLowerCase()
  if (workspaceName.includes(query)) {
    return conversations.slice(0, visibleConversationCount(workspaceId))
  }
  return conversations
    .filter((conversation) => conversationMatchesSidebarSearch(conversation, query))
    .slice(0, visibleConversationCount(workspaceId))
}

function hasHiddenConversationsForSidebar(workspace) {
  const workspaceId = String(workspace?.id || '').trim()
  if (!workspaceId) return false
  const query = normalizedSidebarSearchQuery.value
  if (!query) return hasHiddenConversations(workspaceId)
  const workspaceName = String(workspace?.name || 'Untitled workspace').toLowerCase()
  const matches = workspaceName.includes(query)
    ? conversationsForWorkspace(workspaceId)
    : conversationsForWorkspace(workspaceId).filter((conversation) => (
      conversationMatchesSidebarSearch(conversation, query)
    ))
  return matches.length > visibleConversationCount(workspaceId)
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

// ─── Brand / collapse ─────────────────────────────────────────────────────────
function handleBrandClick() {
  appStore.setSidebarCollapsed(!appStore.isSidebarCollapsed)
}

function toggleSidebarSearch() {
  if (appStore.isSidebarCollapsed) {
    appStore.setSidebarCollapsed(false)
    sidebarSearchOpen.value = true
    return
  }
  sidebarSearchOpen.value = !sidebarSearchOpen.value
  if (!sidebarSearchOpen.value) {
    sidebarSearchQuery.value = ''
  }
}

function openSchemaEditor() {
  appStore.setActiveTab('schema-editor')
}

function openConversationTree() {
  appStore.setActiveTab('conversation-tree')
}

function conversationTimestampValue(conversation) {
  return conversation?.last_turn_at || conversation?.updated_at || conversation?.created_at
}

function formatConversationTimestamp(conversation) {
  if (appStore.isConversationRunning(conversation?.id)) return 'Run'
  return formatCompactRelativeTimestamp(conversationTimestampValue(conversation)) || '-'
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
function clampMenuPosition(x, y, width = 208, height = 128) {
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
    return clampMenuPosition(rect.right - 208, rect.bottom + 4, 208, 128)
  }
  return clampMenuPosition(event?.clientX || 0, event?.clientY || 0, 208, 128)
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
  openSingleConversationMenu(id, clampMenuPosition(event?.clientX || 0, event?.clientY || 0, 208, 128))
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
  pendingDeleteId.value     = conversationId
  deleteDialogTitle.value   = 'Delete Conversation'
  deleteDialogMessage.value = `Are you sure you want to delete "${target?.title || 'Untitled'}"? This action cannot be undone.`
  isDeleteDialogOpen.value  = true
}

function closeDeleteDialog() {
  isDeleteDialogOpen.value  = false
  pendingDeleteId.value     = ''
  deleteDialogTitle.value   = ''
  deleteDialogMessage.value = ''
}

async function confirmDelete() {
  if (!pendingDeleteId.value) return
  try {
    await appStore.deleteConversationById(pendingDeleteId.value)
    removeConversationFromSidebarCache(pendingDeleteId.value)
    toast.success('Conversation Deleted', 'Conversation has been removed.')
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
  window.addEventListener('resize', updateProfileMenuPosition)
  window.addEventListener('scroll', updateProfileMenuPosition, true)
})

onUnmounted(() => {
  window.removeEventListener('sidebar-open-settings', handleOpenSettingsRequest)
  window.removeEventListener('click', handleGlobalClick)
  window.removeEventListener('resize', updateProfileMenuPosition)
  window.removeEventListener('scroll', updateProfileMenuPosition, true)
})

watch(() => appStore.activeWorkspaceId, async (newId) => {
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
    sidebarSearchOpen.value = false
    sidebarSearchQuery.value = ''
  }
})
</script>

<style scoped>
.sidebar-root {
  min-width: 0;
}

.sidebar-brand-row {
  display: flex;
  height: 3.5rem;
  flex-shrink: 0;
  align-items: center;
  border-bottom: 1px solid var(--color-border);
}

.sidebar-brand-button {
  display: flex;
  min-width: 0;
  align-items: center;
  border-radius: 0.5rem;
  color: var(--color-text-main);
  transition:
    background-color var(--motion-duration-standard) var(--motion-ease-standard),
    opacity var(--motion-duration-standard) var(--motion-ease-standard);
}

.sidebar-brand-button:hover {
  background: color-mix(in srgb, var(--color-text-main) 5%, transparent);
}

.sidebar-icon-button {
  display: inline-flex;
  height: 1.875rem;
  width: 1.875rem;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border-radius: 0.5rem;
  color: var(--color-text-muted);
  transition:
    background-color var(--motion-duration-standard) var(--motion-ease-standard),
    color var(--motion-duration-standard) var(--motion-ease-standard);
}

.sidebar-icon-button:hover {
  background: color-mix(in srgb, var(--color-text-main) 7%, transparent);
  color: var(--color-text-main);
}

.sidebar-nav-row,
.sidebar-workspace-row {
  display: flex;
  height: 2.25rem;
  width: 100%;
  align-items: center;
  border-radius: 0.5rem;
  color: var(--color-text-muted);
  overflow: hidden;
  text-align: left;
  transition:
    background-color var(--motion-duration-standard) var(--motion-ease-standard),
    color var(--motion-duration-standard) var(--motion-ease-standard);
}

.sidebar-primary-row {
  color: color-mix(in srgb, var(--color-text-main) 86%, var(--color-text-muted) 14%);
}

.sidebar-nav-row:hover,
.sidebar-workspace-row:hover {
  background: color-mix(in srgb, var(--color-text-main) 5%, transparent);
  color: var(--color-text-main);
}

.sidebar-nav-row-active,
.sidebar-workspace-row-active {
  background: var(--color-selected-surface);
  color: var(--color-text-main);
}

.sidebar-row-icon {
  display: inline-flex;
  height: 1.5rem;
  width: 1.5rem;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
}

.sidebar-row-icon :deep(svg) {
  height: 1.25rem;
  width: 1.25rem;
}

.sidebar-row-label {
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  font-size: 0.8125rem;
  font-weight: 600;
  line-height: 1.25rem;
  transition:
    max-width var(--motion-duration-slow) var(--motion-ease-emphasized),
    opacity var(--motion-duration-standard) var(--motion-ease-standard),
    margin-left var(--motion-duration-slow) var(--motion-ease-emphasized);
}

.sidebar-section-label {
  font-size: 0.75rem;
  font-weight: 700;
  line-height: 1rem;
  color: color-mix(in srgb, var(--color-text-muted) 78%, var(--color-base) 22%);
  letter-spacing: 0.02em;
  text-transform: uppercase;
}

.sidebar-search-input {
  min-height: 2.125rem;
  width: 100%;
  border-radius: 0.5rem;
  border: 1px solid var(--color-border);
  background: color-mix(in srgb, var(--color-base) 78%, var(--color-surface) 22%);
  padding: 0 0.625rem;
  color: var(--color-text-main);
  font-size: 0.8125rem;
  outline: none;
  transition:
    border-color var(--motion-duration-standard) var(--motion-ease-standard),
    background-color var(--motion-duration-standard) var(--motion-ease-standard);
}

.sidebar-search-input::placeholder {
  color: color-mix(in srgb, var(--color-text-muted) 72%, var(--color-base) 28%);
}

.sidebar-search-input:focus {
  border-color: var(--color-selected-border);
  background: var(--color-base);
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
  transition:
    max-width var(--motion-duration-slow) var(--motion-ease-emphasized),
    opacity var(--motion-duration-standard) var(--motion-ease-standard),
    margin-left var(--motion-duration-slow) var(--motion-ease-emphasized) !important;
  will-change: max-width, opacity, margin-left;
}
</style>
