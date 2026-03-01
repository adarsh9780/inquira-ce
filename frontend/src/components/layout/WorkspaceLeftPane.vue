<template>
  <div class="flex h-full flex-col">
    <div class="flex-shrink-0 border-b px-4 py-2 flex items-center gap-4" style="background-color: var(--color-base); border-color: var(--color-border);">
      <div class="inline-flex rounded-lg border p-1 flex-shrink-0" style="border-color: var(--color-border); background-color: var(--color-base);">
        <button
          @click="appStore.setWorkspacePane('code')"
          class="rounded-md px-3 py-1.5 text-sm font-medium transition-colors"
          :class="appStore.workspacePane === 'code' ? 'bg-white shadow-sm' : ''"
          :style="appStore.workspacePane === 'code' ? 'color: var(--color-text-main);' : 'color: var(--color-text-muted);'"
        >
          Code
        </button>
        <button
          @click="appStore.setWorkspacePane('chat')"
          class="rounded-md px-3 py-1.5 text-sm font-medium transition-colors"
          :class="appStore.workspacePane === 'chat' ? 'bg-white shadow-sm' : ''"
          :style="appStore.workspacePane === 'chat' ? 'color: var(--color-text-main);' : 'color: var(--color-text-muted);'"
        >
          Chat
        </button>
      </div>
      
      <!-- Teleport Target for Code/Chat Toolbar -->
      <div id="workspace-left-pane-toolbar" class="flex-1 min-w-0 flex items-center justify-end"></div>
    </div>

    <div class="min-h-0 flex-1 p-3 sm:p-4 pb-0">
      <div v-show="appStore.workspacePane === 'code'" class="h-full">
        <CodeTab />
      </div>
      <div v-show="appStore.workspacePane === 'chat'" class="h-full">
        <ChatTab />
      </div>
    </div>
  </div>
</template>

<script setup>
import { useAppStore } from '../../stores/appStore'
import CodeTab from '../analysis/CodeTab.vue'
import ChatTab from '../chat/ChatTab.vue'

const appStore = useAppStore()
</script>
