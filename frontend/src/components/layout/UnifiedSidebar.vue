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
        <div
          class="rounded-[24px] border shadow-sm overflow-hidden"
          style="border-color: color-mix(in srgb, var(--color-border) 82%, transparent); background: linear-gradient(180deg, color-mix(in srgb, var(--color-surface) 92%, var(--color-base)) 0%, color-mix(in srgb, var(--color-surface) 72%, transparent) 100%);"
        >
          <div class="px-3 pt-3 pb-2 border-b" style="border-color: color-mix(in srgb, var(--color-border) 78%, transparent);">
            <p class="text-[10px] font-semibold uppercase tracking-[0.12em]" style="color: var(--color-text-muted);">Navigation</p>
            <p class="text-sm font-semibold mt-1" style="color: var(--color-text-main);">Workspace explorer</p>
            <p class="text-[11px] mt-1" style="color: var(--color-text-muted);">
              Pick one workspace, then browse its datasets and conversations.
            </p>
          </div>

          <SidebarWorkspaces
            :is-collapsed="false"
            @header-click="handleExplorerHeaderClick"
            @select="handleWorkspaceSelect"
          />

          <Transition name="sidebar-section">
            <div v-if="appStore.hasWorkspace" class="px-1 pb-2">
              <div class="mx-2 rounded-2xl border px-1 py-2" style="border-color: color-mix(in srgb, var(--color-border) 78%, transparent); background-color: color-mix(in srgb, var(--color-base) 80%, transparent);">
                <SidebarDatasets
                  :is-collapsed="false"
                  @header-click="handleExplorerHeaderClick"
                  @select="handleDatasetSelect"
                  @open-settings="openSettings"
                />
                <div class="mx-3 my-1 h-px" style="background-color: color-mix(in srgb, var(--color-border) 78%, transparent);" />
                <SidebarConversations
                  :is-collapsed="false"
                  @header-click="handleExplorerHeaderClick"
                  @select="handleConversationSelect"
                />
              </div>
            </div>
          </Transition>
        </div>
      </div>
    </div>

    <div class="border-t p-2 shrink-0 flex flex-col gap-2" style="border-color: var(--color-border); background-color: var(--color-base);">
      <button
        @click="handleTabClick('workspace')"
        class="w-full flex items-center justify-between p-2 rounded-lg transition-colors"
        :style="appStore.activeTab === 'workspace' ? 'background-color: color-mix(in srgb, var(--color-text-main) 8%, transparent); color: var(--color-text-main);' : 'color: var(--color-text-muted);'"
        title="Workspace"
      >
        <div class="flex items-center gap-2 min-w-0">
          <FolderOpenIcon class="w-4 h-4 shrink-0" />
          <span class="text-xs font-medium truncate" :class="appStore.activeTab === 'workspace' ? 'font-semibold' : ''">Workspace</span>
        </div>
      </button>

      <button
        @click="handleTabClick('schema-editor')"
        class="w-full flex items-center justify-between p-2 rounded-lg transition-colors"
        :style="appStore.activeTab === 'schema-editor' ? 'background-color: color-mix(in srgb, var(--color-text-main) 8%, transparent); color: var(--color-text-main);' : 'color: var(--color-text-muted);'"
        title="Schema Editor"
      >
        <div class="flex items-center gap-2 min-w-0">
          <DocumentTextIcon class="w-4 h-4 shrink-0" />
          <span class="text-xs font-medium truncate" :class="appStore.activeTab === 'schema-editor' ? 'font-semibold' : ''">Schema Editor</span>
        </div>
      </button>
    </div>

    <SettingsModal
      :is-open="isSettingsOpen"
      :initial-tab="settingsInitialTab"
      @close="closeSettings"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAppStore } from '../../stores/appStore'
import SettingsModal from '../modals/SettingsModal.vue'
import SidebarWorkspaces from './sidebar/SidebarWorkspaces.vue'
import SidebarDatasets from './sidebar/SidebarDatasets.vue'
import SidebarConversations from './sidebar/SidebarConversations.vue'
import logo from '../../assets/favicon.svg'

import {
  DocumentTextIcon,
  FolderOpenIcon
} from '@heroicons/vue/24/outline'

const appStore = useAppStore()

const isSettingsOpen = ref(false)
const settingsInitialTab = ref('api')

function handleTabClick(tabId) {
  const normalized = String(tabId || '').trim().toLowerCase()
  if (normalized === 'schema-editor') {
    if (appStore.activeTab === 'schema-editor') {
      appStore.setSidebarCollapsed(true)
      return
    }
    appStore.setActiveTab('schema-editor')
    return
  }
  if (normalized === 'workspace') {
    if (appStore.activeTab === 'workspace') {
      appStore.setSidebarCollapsed(true)
      return
    }
    appStore.setActiveTab('workspace')
    return
  }
  appStore.setActiveTab(tabId)
}

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
</style>
