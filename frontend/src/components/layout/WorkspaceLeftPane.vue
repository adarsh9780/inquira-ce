<template>
  <div class="flex h-full flex-col">
    <div class="flex-shrink-0 border-b border-gray-200 bg-white px-4 py-2 flex items-center gap-4">
      <div class="inline-flex rounded-lg border border-gray-200 bg-gray-50 p-1 flex-shrink-0">
        <button
          @click="appStore.setWorkspacePane('code')"
          class="rounded-md px-3 py-1.5 text-sm font-medium transition-colors"
          :class="appStore.workspacePane === 'code' ? 'bg-white text-blue-700 shadow-sm' : 'text-gray-600 hover:text-gray-900'"
        >
          Code
        </button>
        <button
          @click="appStore.setWorkspacePane('chat')"
          class="rounded-md px-3 py-1.5 text-sm font-medium transition-colors"
          :class="appStore.workspacePane === 'chat' ? 'bg-white text-blue-700 shadow-sm' : 'text-gray-600 hover:text-gray-900'"
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
