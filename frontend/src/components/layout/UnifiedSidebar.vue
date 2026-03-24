<template>
  <div
    class="flex flex-col w-72 border-r h-full shrink-0 z-40 shadow-sm relative overflow-visible"
    style="background-color: var(--color-base); border-color: var(--color-border);"
  >
    <div
      class="h-16 flex items-center px-3 border-b shrink-0 cursor-pointer hover:bg-zinc-100/70 transition-colors"
      @click="toggleSidebar"
      style="border-color: var(--color-border);"
      title="Click to collapse/expand"
    >
      <div class="flex items-center justify-center w-full">
        <div class="flex items-center justify-start w-full min-w-0">
          <img :src="logo" alt="Inquira Logo" class="w-8 h-8 rounded shrink-0 shadow-sm" />
          <div class="ml-3 min-w-0">
            <h1 class="text-sm font-bold tracking-tight leading-none truncate" style="color: var(--color-text-main);">Inquira</h1>
            <p class="text-[10px] font-medium mt-0.5 truncate" style="color: var(--color-text-muted);">LLM-Powered Analysis</p>
          </div>
        </div>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto overflow-x-hidden flex flex-col py-3 custom-scrollbar">
      <div class="px-3">
        <SidebarWorkspaces
          :is-collapsed="false"
          @header-click="handleExplorerHeaderClick"
          @select="handleWorkspaceSelect"
        />

        <Transition name="sidebar-section">
          <div v-if="appStore.hasWorkspace" class="mt-2">
            <div class="mx-0 h-px" style="background-color: color-mix(in srgb, var(--color-border) 78%, transparent);" />
            <SidebarDatasets
              :is-collapsed="false"
              @header-click="handleExplorerHeaderClick"
              @select="handleDatasetSelect"
              @open-settings="openSettings"
            />
            <div class="mx-0 mt-1 h-px" style="background-color: color-mix(in srgb, var(--color-border) 78%, transparent);" />
            <SidebarConversations
              :is-collapsed="false"
              @header-click="handleExplorerHeaderClick"
              @select="handleConversationSelect"
            />
          </div>
        </Transition>
      </div>
    </div>

    <div class="border-t p-2 shrink-0 flex flex-col gap-1" style="border-color: var(--color-border); background-color: var(--color-base);">
      <button
        @click="openSettings('api')"
        class="w-full flex items-center gap-2 p-2 rounded-lg hover:bg-zinc-100/70 transition-colors"
        style="color: var(--color-text-main);"
        title="Settings"
      >
        <CogIcon class="w-4 h-4 shrink-0" />
        <span class="text-xs font-medium">Settings</span>
      </button>

      <button
        @click="openTerms"
        class="w-full flex items-center gap-2 p-2 rounded-lg hover:bg-zinc-100/70 transition-colors"
        style="color: var(--color-text-main);"
        title="Terms & Conditions"
      >
        <DocumentIcon class="w-4 h-4 shrink-0" />
        <span class="text-xs font-medium">Terms & Conditions</span>
      </button>

      <div class="border-t my-1" style="border-color: var(--color-border);"></div>

      <button
        @click="promptLogout"
        class="w-full flex items-center gap-2 p-2 rounded-lg hover:bg-red-50 transition-colors"
        style="color: #dc2626;"
        title="Logout"
      >
        <ArrowRightOnRectangleIcon class="w-4 h-4 shrink-0" />
        <span class="text-xs font-medium">Logout</span>
      </button>
    </div>

    <SettingsModal
      :is-open="isSettingsOpen"
      :initial-tab="settingsInitialTab"
      @close="closeSettings"
    />
    <ConfirmationModal
      :is-open="isLogoutConfirmOpen"
      title="Confirm Logout"
      :message="`Are you sure you want to log out, ${accountDisplayLabel}?`"
      confirm-text="Log Out"
      cancel-text="Cancel"
      @close="cancelLogout"
      @confirm="confirmLogout"
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
            <p class="text-sm font-semibold">Terms &amp; Conditions</p>
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
import { ref, computed, onMounted, onUnmounted } from 'vue'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'
import { useAppStore } from '../../stores/appStore'
import { useAuthStore } from '../../stores/authStore'
import SettingsModal from '../modals/SettingsModal.vue'
import ConfirmationModal from '../modals/ConfirmationModal.vue'
import SidebarWorkspaces from './sidebar/SidebarWorkspaces.vue'
import SidebarDatasets from './sidebar/SidebarDatasets.vue'
import SidebarConversations from './sidebar/SidebarConversations.vue'
import logo from '../../assets/favicon.svg'
import apiService from '../../services/apiService'

import {
  CogIcon,
  DocumentIcon,
  ArrowRightOnRectangleIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'

const appStore = useAppStore()
const authStore = useAuthStore()

const isSettingsOpen = ref(false)
const settingsInitialTab = ref('api')
const isTermsDialogOpen = ref(false)
const isTermsLoading = ref(false)
const termsError = ref('')
const termsMarkdown = ref('')
const termsLastUpdated = ref('')
const isLogoutConfirmOpen = ref(false)

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

const accountDisplayLabel = computed(() => {
  const value = String(authStore.username || '').trim()
  if (!value) return 'Account'
  if (value.includes('@')) return value
  if (!value.includes(' ')) {
    return value.charAt(0).toUpperCase() + value.slice(1)
  }
  return value
    .split(/\s+/)
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1).toLowerCase())
    .join(' ')
})

function toggleSidebar() {
  appStore.setSidebarCollapsed(true)
}

function handleExplorerHeaderClick() {
  // Explorer sections manage their own expanded state.
}

function handleWorkspaceSelect() {
  appStore.setActiveTab('workspace')
}

function handleDatasetSelect() {
  appStore.setActiveTab('workspace')
}

function handleConversationSelect() {
  appStore.setActiveTab('workspace')
}

function openSettings(tab = 'api') {
  settingsInitialTab.value = tab
  isSettingsOpen.value = true
}

function closeSettings() {
  isSettingsOpen.value = false
  settingsInitialTab.value = 'api'
}

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

function promptLogout() {
  isLogoutConfirmOpen.value = true
}

function cancelLogout() {
  isLogoutConfirmOpen.value = false
}

async function confirmLogout() {
  isLogoutConfirmOpen.value = false
  try {
    await authStore.logout()
  } catch (error) {
    console.error('Logout failed:', error)
  }
}
</script>

<style scoped>
.sidebar-section-enter-active,
.sidebar-section-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.sidebar-section-enter-from,
.sidebar-section-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.custom-scrollbar::-webkit-scrollbar {
  width: 5px;
  height: 5px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #e2e8f0;
  border-radius: 4px;
}

.custom-scrollbar:hover::-webkit-scrollbar-thumb {
  background: #cbd5e1;
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
