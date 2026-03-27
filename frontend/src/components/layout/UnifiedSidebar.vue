<template>
  <div
    class="flex flex-col w-72 h-full shrink-0 z-40 relative overflow-visible border-r"
    style="background-color: var(--color-base); border-color: var(--color-border);"
  >
    <!-- Header with Logo -->
    <div
      class="h-14 flex items-center px-4 shrink-0 cursor-pointer transition-all duration-200 hover:brightness-98 active:brightness-95"
      @click="toggleSidebar"
      title="Click to collapse/expand"
    >
      <div class="flex items-center gap-3">
        <img :src="logo" alt="Inquira" class="w-8 h-8 rounded-lg shadow-sm" />
        <div>
          <h1 class="text-sm font-bold tracking-tight leading-none" style="color: var(--color-text-main);">Inquira</h1>
          <p class="text-[10px] font-medium mt-0.5" style="color: var(--color-text-muted);">LLM-Powered Analysis</p>
        </div>
      </div>
    </div>



    <!-- Scrollable Content -->
    <div class="flex-1 overflow-y-auto overflow-x-hidden flex flex-col custom-scrollbar">
      <div class="px-3 py-3 space-y-1">
        <!-- Workspaces Section -->
        <div class="space-y-0.5">
          <!-- Section Header -->
          <button
            @click="workspacesExpanded = !workspacesExpanded"
            class="w-full flex items-center justify-between px-2 py-1.5 rounded-lg transition-colors hover:bg-[var(--color-surface)]"
          >
            <div class="flex items-center gap-2">
              <BuildingOffice2Icon class="w-3.5 h-3.5" style="color: var(--color-text-muted);" />
              <span class="text-[11px] uppercase tracking-[0.08em] font-semibold" style="color: var(--color-text-muted);">Workspace</span>
              <span
                v-if="appStore.workspaces.length > 0"
                class="text-[10px] px-1.5 py-0.5 rounded-full font-medium"
                style="background-color: var(--color-surface); color: var(--color-text-muted);"
              >
                {{ appStore.workspaces.length }}
              </span>
            </div>
            <ChevronRightIcon
              class="w-3.5 h-3.5 transition-transform duration-200"
              :class="workspacesExpanded ? 'rotate-90' : ''"
              style="color: var(--color-text-muted);"
            />
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

            <div v-if="filteredWorkspaces.length === 0 && appStore.workspaces.length > 0" class="px-2 py-2 text-xs" style="color: var(--color-text-muted);">
              No matches found
            </div>

            <div v-if="appStore.workspaces.length === 0" class="px-2 py-2 text-xs" style="color: var(--color-text-muted);">
              No workspaces yet
            </div>

            <Listbox v-else :model-value="selectedWorkspaceId" @update:model-value="selectWorkspace">
              <div class="relative">
                <ListboxButton
                  class="w-full rounded-lg px-3 py-2.5 text-left transition-colors hover:bg-[var(--color-surface)]"
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
                      v-for="ws in filteredWorkspaces"
                      :key="ws.id"
                      :value="ws.id"
                      as="template"
                      v-slot="{ active, selected }"
                      :disabled="isWorkspaceDeleting(ws.id)"
                    >
                      <li
                        class="group/item flex items-center justify-between gap-2 rounded-lg px-3 py-2 transition-colors relative"
                        :class="[
                          active ? 'bg-[var(--color-surface)]' : '',
                          selected ? 'bg-emerald-50 text-emerald-800' : '',
                          isWorkspaceDeleting(ws.id) ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'
                        ]"
                      >
                        <div class="flex items-center gap-2 min-w-0 flex-1">
                          <CheckCircleIcon v-if="selected" class="w-4 h-4 shrink-0 text-emerald-600" />
                          <BuildingOffice2Icon v-else class="w-4 h-4 shrink-0" style="color: var(--color-text-muted);" />
                          <span class="truncate text-sm" :class="selected ? 'font-semibold' : 'font-medium'">{{ ws.name }}</span>
                        </div>
                        <div class="flex items-center gap-1">
                          <button
                            v-if="!isWorkspaceDeleting(ws.id)"
                            @click.stop="confirmDeleteWorkspace(ws.id)"
                            class="btn-icon p-1 rounded transition-all duration-150 opacity-0 group-hover/item:opacity-100"
                            style="color: var(--color-text-muted);"
                            title="Delete Workspace"
                          >
                            <TrashIcon class="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </li>
                    </ListboxOption>
                  </ListboxOptions>
                </transition>
              </div>
            </Listbox>

            <!-- Add Workspace Button -->
            <button
              @click="openCreateDialog"
              class="w-full flex items-center gap-2 px-3 py-2 mt-1 rounded-lg text-xs transition-colors hover:bg-[var(--color-surface)]"
              style="color: var(--color-text-muted);"
            >
              <PlusIcon class="w-3.5 h-3.5" />
              <span>New Workspace</span>
            </button>
          </div>
        </div>

        <!-- Datasets Section -->
        <div v-if="appStore.hasWorkspace" class="space-y-0.5">
          <div class="h-px my-2" style="background-color: color-mix(in srgb, var(--color-border) 50%, transparent);" />

          <!-- Section Header -->
          <div class="flex items-center justify-between px-2 py-1.5">
            <button
              @click="datasetsExpanded = !datasetsExpanded"
              class="flex items-center gap-2 rounded-lg transition-colors hover:bg-[var(--color-surface)] px-1 py-0.5"
            >
              <ChevronRightIcon
                class="w-3.5 h-3.5 transition-transform duration-200"
                :class="datasetsExpanded ? 'rotate-90' : ''"
                style="color: var(--color-text-muted);"
              />
              <CircleStackIcon class="w-3.5 h-3.5" style="color: var(--color-text-muted);" />
              <span class="text-[11px] uppercase tracking-[0.08em] font-semibold" style="color: var(--color-text-muted);">Datasets</span>
              <span
                v-if="localDatasets.length > 0"
                class="text-[10px] px-1.5 py-0.5 rounded-full font-medium"
                style="background-color: var(--color-surface); color: var(--color-text-muted);"
              >
                {{ localDatasets.length }}
              </span>
            </button>
            <button
              v-if="appStore.hasWorkspace"
              @click.stop="openSettings('data')"
              class="btn-icon shrink-0"
              title="Add Dataset"
            >
              <PlusIcon class="w-3.5 h-3.5" />
            </button>
          </div>

          <!-- Section Content -->
          <div v-show="datasetsExpanded" class="pl-2">
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

            <div v-else class="space-y-0.5 pb-1">
              <div
                v-for="ds in filteredDatasets"
                :key="ds.table_name"
                class="group flex items-center justify-between gap-2 px-3 py-2 rounded-lg transition-colors cursor-pointer hover:bg-[var(--color-surface)]"
                :class="{ 'bg-[var(--color-surface)]': appStore.activeDatasetId === ds.table_name }"
                @click="selectDataset(ds)"
              >
                <div class="flex items-center gap-2 min-w-0 flex-1">
                  <CircleStackIcon class="w-3.5 h-3.5 shrink-0" :class="appStore.activeDatasetId === ds.table_name ? 'text-emerald-600' : ''" style="color: var(--color-text-muted);" />
                  <div class="min-w-0 flex-1">
                    <p class="truncate text-xs font-medium" :class="appStore.activeDatasetId === ds.table_name ? 'text-emerald-700' : ''" style="color: var(--color-text-main);">{{ ds.table_name }}</p>
                    <p v-if="ds.file_path" class="truncate text-[10px]" :class="appStore.activeDatasetId === ds.table_name ? 'text-emerald-700/70' : ''" style="color: var(--color-text-muted);">{{ ds.file_path }}</p>
                  </div>
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
        <div v-if="appStore.hasWorkspace" class="space-y-0.5">
          <div class="h-px my-2" style="background-color: color-mix(in srgb, var(--color-border) 50%, transparent);" />

          <!-- Section Header -->
          <button
            @click="conversationsExpanded = !conversationsExpanded"
            class="w-full flex items-center justify-between px-2 py-1.5 rounded-lg transition-colors hover:bg-[var(--color-surface)]"
          >
            <div class="flex items-center gap-2">
              <ChatBubbleLeftEllipsisIcon class="w-3.5 h-3.5" style="color: var(--color-text-muted);" />
              <span class="text-[11px] uppercase tracking-[0.08em] font-semibold" style="color: var(--color-text-muted);">Conversations</span>
              <span
                v-if="appStore.conversations.length > 0"
                class="text-[10px] px-1.5 py-0.5 rounded-full font-medium"
                style="background-color: var(--color-surface); color: var(--color-text-muted);"
              >
                {{ appStore.conversations.length }}
              </span>
            </div>
            <ChevronRightIcon
              class="w-3.5 h-3.5 transition-transform duration-200"
              :class="conversationsExpanded ? 'rotate-90' : ''"
              style="color: var(--color-text-muted);"
            />
          </button>

          <!-- Section Content -->
          <div v-show="conversationsExpanded" class="pl-2">
            <div v-if="filteredConversations.length === 0 && appStore.conversations.length > 0" class="px-2 py-2 text-xs" style="color: var(--color-text-muted);">
              No matches found
            </div>

            <div v-if="appStore.conversations.length === 0" class="px-2 py-2 text-xs" style="color: var(--color-text-muted);">
              No conversations yet
            </div>

            <div v-else class="space-y-0.5 pb-1">
              <div
                v-for="conv in filteredConversations"
                :key="conv.id"
                class="group flex items-center justify-between gap-2 px-3 py-2 rounded-lg transition-colors cursor-pointer hover:bg-[var(--color-surface)]"
                :class="{ 'bg-[var(--color-surface)]': appStore.activeConversationId === conv.id }"
                @click="selectConversation(conv.id)"
              >
                <div class="flex items-start gap-2 min-w-0 pr-2 pt-0.5 flex-1" @dblclick="startEditing(conv)">
                  <ChatBubbleLeftRightIcon class="w-3.5 h-3.5 shrink-0 mt-0.5" :class="appStore.activeConversationId === conv.id ? 'text-emerald-600' : ''" style="color: var(--color-text-muted);" />
                  <div class="flex-1 min-w-0">
                    <div v-if="editingId === conv.id" class="flex items-center gap-1 w-full relative z-10">
                      <input
                        :ref="(el) => { if (el) editInputs[conv.id] = el }"
                        v-model="editingTitleValue"
                        class="input-base py-0.5 px-1 text-xs font-semibold"
                        @keydown.enter.prevent="saveTitle(conv.id)"
                        @keydown.esc.prevent="cancelEditing"
                        @blur="saveTitle(conv.id)"
                        @click.stop
                      />
                    </div>
                    <template v-else>
                      <p
                        class="truncate"
                        :class="conv.id === appStore.activeConversationId ? 'font-semibold' : 'font-medium'"
                        :title="conv.title || 'Untitled'"
                      >
                        {{ conv.title || 'Untitled' }}
                      </p>
                    </template>
                  </div>
                </div>
                <div v-if="editingId !== conv.id" class="flex-shrink-0 flex items-center opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    @click.stop="startEditing(conv)"
                    class="btn-icon p-1 rounded hover:text-blue-600"
                    style="color: var(--color-text-muted);"
                    title="Rename Conversation"
                  >
                    <PencilIcon class="w-3.5 h-3.5" />
                  </button>
                  <button
                    @click.stop="confirmDeleteConversation(conv.id)"
                    class="btn-icon p-1 rounded hover:text-red-500"
                    style="color: var(--color-text-muted);"
                    title="Delete Conversation"
                  >
                    <TrashIcon class="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Search Bar (Animated) -->
    <Transition name="search-bar">
      <div v-if="isSearchOpen" class="px-3 py-3 border-t" style="border-color: var(--color-border);">
        <div class="relative">
          <MagnifyingGlassIcon class="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 pointer-events-none" style="color: var(--color-text-muted);" />
          <input
            ref="searchInputRef"
            v-model="searchQuery"
            type="text"
            placeholder="Search..."
            class="w-full pl-9 pr-3 py-2 text-xs rounded-lg border transition-all duration-150 placeholder:text-[var(--color-text-muted)] focus:outline-none focus:ring-2"
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
    <div class="border-t p-3 shrink-0 flex items-center justify-center gap-4" style="border-color: var(--color-border); background-color: var(--color-base);">
      <button
        @click="openSettings('api')"
        class="relative group flex items-center justify-center p-2 rounded-lg transition-all duration-200 hover:bg-[var(--color-surface)]"
        style="color: var(--color-text-main);"
        title="Settings"
      >
        <CogIcon class="w-4 h-4" />
        <span class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 text-[10px] rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" style="background-color: var(--color-surface); color: var(--color-text-main);">
          Settings
        </span>
      </button>

      <button
        @click="toggleSearch"
        class="relative group flex items-center justify-center p-2 rounded-lg transition-all duration-200 hover:bg-[var(--color-surface)]"
        style="color: var(--color-text-main);"
        title="Search"
      >
        <MagnifyingGlassIcon class="w-4 h-4" />
        <span class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 text-[10px] rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" style="background-color: var(--color-surface); color: var(--color-text-main);">
          Search
        </span>
      </button>

      <button
        @click="openTerms"
        class="relative group flex items-center justify-center p-2 rounded-lg transition-all duration-200 hover:bg-[var(--color-surface)]"
        style="color: var(--color-text-main);"
        title="Terms & Conditions"
      >
        <ScaleIcon class="w-4 h-4" />
        <span class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 text-[10px] rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" style="background-color: var(--color-surface); color: var(--color-text-main);">
          Terms & Conditions
        </span>
      </button>
    </div>

    <SettingsModal
      :is-open="isSettingsOpen"
      :initial-tab="settingsInitialTab"
      @close="closeSettings"
    />

    <WorkspaceCreateModal
      :is-open="isCreateDialogOpen"
      :is-submitting="isCreatingWorkspace"
      :plan="authStore.planLabel"
      @close="closeCreateDialog"
      @submit="createWorkspace"
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
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'
import { Listbox, ListboxButton, ListboxOption, ListboxOptions } from '@headlessui/vue'
import { useAppStore } from '../../stores/appStore'
import { useAuthStore } from '../../stores/authStore'
import { toast } from '../../composables/useToast'
import { extractApiErrorMessage } from '../../utils/apiError'
import SettingsModal from '../modals/SettingsModal.vue'
import WorkspaceCreateModal from '../modals/WorkspaceCreateModal.vue'
import ConfirmationModal from '../modals/ConfirmationModal.vue'
import logo from '../../assets/favicon.svg'
import apiService from '../../services/apiService'

import {
  BuildingOffice2Icon,
  CheckCircleIcon,
  ChevronUpDownIcon,
  ChevronRightIcon,
  PlusIcon,
  PencilIcon,
  TrashIcon,
  CogIcon,
  ScaleIcon,
  XMarkIcon,
  MagnifyingGlassIcon,
  CircleStackIcon,
  ChatBubbleLeftEllipsisIcon,
  ChatBubbleLeftRightIcon,
} from '@heroicons/vue/24/outline'

const appStore = useAppStore()
const authStore = useAuthStore()

// Search
const searchQuery = ref('')
const isSearchOpen = ref(false)

// Conversation editing
const editingId = ref(null)
const editingTitleValue = ref('')
const editInputs = ref({})
const searchInputRef = ref(null)

function toggleSearch() {
  isSearchOpen.value = !isSearchOpen.value
  if (isSearchOpen.value) {
    nextTick(() => {
      searchInputRef.value?.focus()
    })
  } else {
    searchQuery.value = ''
  }
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
const settingsInitialTab = ref('api')

// Terms dialog
const isTermsDialogOpen = ref(false)
const isTermsLoading = ref(false)
const termsError = ref('')
const termsMarkdown = ref('')
const termsLastUpdated = ref('')

// Create workspace
const isCreateDialogOpen = ref(false)
const isCreatingWorkspace = ref(false)

// Delete confirmation
const isDeleteDialogOpen = ref(false)
const deleteDialogTitle = ref('')
const deleteDialogMessage = ref('')
const pendingDeleteType = ref('')
const pendingDeleteId = ref('')

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
const filteredWorkspaces = computed(() => {
  if (!searchQuery.value) return appStore.workspaces
  const query = searchQuery.value.toLowerCase()
  return appStore.workspaces.filter(ws => ws.name?.toLowerCase().includes(query))
})

const filteredDatasets = computed(() => {
  if (!searchQuery.value) return localDatasets.value
  const query = searchQuery.value.toLowerCase()
  return localDatasets.value.filter(ds => ds.table_name?.toLowerCase().includes(query))
})

const filteredConversations = computed(() => {
  if (!searchQuery.value) return appStore.conversations
  const query = searchQuery.value.toLowerCase()
  return appStore.conversations.filter(conv => conv.title?.toLowerCase().includes(query))
})

// Selected workspace
const selectedWorkspaceId = computed(() => String(appStore.activeWorkspaceId || '').trim())
const activeWorkspaceName = computed(() => {
  const activeId = selectedWorkspaceId.value
  const activeWorkspace = appStore.workspaces.find((ws) => ws.id === activeId)
  return activeWorkspace?.name || 'Choose a workspace'
})

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
      file_path: item.file_path,
    }))
    localDatasets.value = catalogDatasets
  } catch (error) {
    console.error('Failed to load datasets:', error)
    localDatasets.value = []
  } finally {
    isLoadingDatasets.value = false
  }
}

function isWorkspaceDeleting(workspaceId) {
  return appStore.workspaceDeletionJobs.some((job) => job.workspace_id === workspaceId)
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

function selectDataset(ds) {
  if (!ds || !ds.table_name) return
  appStore.setActiveDataset(ds.table_name)
  if (ds.file_path) {
    appStore.setActiveDatasetPath(ds.file_path)
  }
}

function selectConversation(id) {
  appStore.setActiveConversation(id)
}

function startEditing(conv) {
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

// Toggle sidebar
function toggleSidebar() {
  appStore.setSidebarCollapsed(true)
}

// Settings
function openSettings(tab = 'api') {
  settingsInitialTab.value = tab
  isSettingsOpen.value = true
}

function closeSettings() {
  isSettingsOpen.value = false
  settingsInitialTab.value = 'api'
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

// Create workspace
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
    if (ws?.id) {
      await selectWorkspace(ws.id)
    }
  } catch (error) {
    toast.error('Workspace Error', extractApiErrorMessage(error, 'Failed to create workspace'))
  } finally {
    isCreatingWorkspace.value = false
  }
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
    if (pendingDeleteType.value === 'workspace') {
      const job = await appStore.deleteWorkspaceAsync(pendingDeleteId.value)
      toast.info('Workspace Deletion Started', `Deleting workspace in background (job: ${job.job_id.slice(0, 8)}...).`)
    } else if (pendingDeleteType.value === 'dataset') {
      const workspaceId = appStore.activeWorkspaceId
      if (workspaceId) {
        await apiService.v1DeleteDataset(workspaceId, pendingDeleteId.value)
        toast.success('Dataset Deleted', 'Dataset has been removed.')
        await fetchDatasets()
      }
    } else if (pendingDeleteType.value === 'conversation') {
      await apiService.v1DeleteConversation(pendingDeleteId.value)
      await appStore.fetchConversations()
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
  } catch {
    // Ignore bootstrap failures here. The parent app handles global state recovery.
  }
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
