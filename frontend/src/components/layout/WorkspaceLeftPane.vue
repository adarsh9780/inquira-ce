<template>
  <div class="flex h-full w-full min-h-0 min-w-0 flex-col" style="background-color: var(--color-workspace-surface);">
    <div class="flex-shrink-0 h-16 px-4 flex items-center gap-4" style="background-color: var(--color-workspace-surface);">
      <div class="inline-flex rounded-xl border p-1 flex-shrink-0" style="border-color: var(--color-border); background-color: var(--color-control-surface);">
        <button
          @click="appStore.setWorkspacePane('code')"
          class="rounded-lg px-3 py-1.5 text-sm font-medium transition-colors"
          :style="appStore.workspacePane === 'code'
            ? 'background-color: var(--color-selected-surface); color: var(--color-text-main); box-shadow: inset 0 0 0 1px var(--color-selected-border);'
            : 'color: var(--color-text-muted);'"
        >
          Code
        </button>
        <button
          @click="appStore.setWorkspacePane('chat')"
          class="rounded-lg px-3 py-1.5 text-sm font-medium transition-colors"
          :style="appStore.workspacePane === 'chat'
            ? 'background-color: var(--color-selected-surface); color: var(--color-text-main); box-shadow: inset 0 0 0 1px var(--color-selected-border);'
            : 'color: var(--color-text-muted);'"
        >
          Chat
        </button>
      </div>
      
      <!-- Teleport Target for Code/Chat Toolbar -->
      <div id="workspace-left-pane-toolbar" class="flex-1 min-w-0 flex items-center justify-end"></div>
    </div>

    <div class="min-h-0 flex-1 flex flex-col p-3 sm:p-4 pb-0">
      <div class="min-h-0 flex-1">
      <div v-show="appStore.workspacePane === 'code'" class="h-full">
        <CodeTab />
      </div>
      <div v-show="appStore.workspacePane === 'chat'" class="h-full">
        <ChatTab />
      </div>
      </div>

      <div class="flex-shrink-0 pt-2 sm:pt-3" style="background-color: var(--color-workspace-surface);">
        <ChatInput />
      </div>
    </div>
  </div>
</template>

<script setup>
import { useAppStore } from '../../stores/appStore'
import CodeTab from '../analysis/CodeTab.vue'
import ChatTab from '../chat/ChatTab.vue'
import ChatInput from '../chat/ChatInput.vue'

const appStore = useAppStore()
</script>
