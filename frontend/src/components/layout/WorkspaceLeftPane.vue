<template>
  <div class="flex h-full w-full min-h-0 min-w-0 flex-col" style="background-color: var(--color-workspace-surface);">
    <div class="flex-shrink-0 h-16 px-4 flex items-center gap-4" style="background-color: var(--color-workspace-surface);">
      <div class="inline-flex items-center gap-1 flex-shrink-0">
        <button
          @click="appStore.setWorkspacePane('code')"
          class="workspace-pane-tab"
          :style="appStore.workspacePane === 'code'
            ? 'color: var(--color-text-main); box-shadow: inset 0 -2px 0 0 var(--color-accent);'
            : 'color: var(--color-text-muted);'"
        >
          Code
        </button>
        <button
          @click="appStore.setWorkspacePane('chat')"
          class="workspace-pane-tab"
          :style="appStore.workspacePane === 'chat'
            ? 'color: var(--color-text-main); box-shadow: inset 0 -2px 0 0 var(--color-accent);'
            : 'color: var(--color-text-muted);'"
        >
          Chat
        </button>
        <button
          @click="appStore.setWorkspacePane('ctree')"
          class="workspace-pane-tab"
          :style="appStore.workspacePane === 'ctree'
            ? 'color: var(--color-text-main); box-shadow: inset 0 -2px 0 0 var(--color-accent);'
            : 'color: var(--color-text-muted);'"
        >
          Ctree
        </button>
      </div>
      
      <!-- Teleport Target for Code/Chat Toolbar -->
      <div id="workspace-left-pane-toolbar" class="flex-1 min-w-0 flex items-center justify-end"></div>
    </div>

    <div
      class="min-h-0 flex-1 flex flex-col p-3 sm:p-4 pb-0"
      :class="['workspace-left-content', { 'workspace-left-content-chat-only': isChatOnlyMode }]"
    >
      <div class="min-h-0 flex-1">
      <div v-show="appStore.workspacePane === 'code'" class="h-full">
        <CodeTab />
      </div>
      <div v-show="appStore.workspacePane === 'chat'" class="h-full">
        <ChatTab />
      </div>
      <div v-show="appStore.workspacePane === 'ctree'" class="h-full">
        <SidebarGlobalTurnTree variant="page" />
      </div>
      </div>

      <div class="flex-shrink-0 pt-2 sm:pt-3" style="background-color: var(--color-workspace-surface);">
        <ChatInput />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useAppStore } from '../../stores/appStore'
import CodeTab from '../analysis/CodeTab.vue'
import ChatTab from '../chat/ChatTab.vue'
import ChatInput from '../chat/ChatInput.vue'
import SidebarGlobalTurnTree from './sidebar/SidebarGlobalTurnTree.vue'

const appStore = useAppStore()
const isChatOnlyMode = computed(() => appStore.workspacePane === 'chat' && appStore.workspaceLayoutMode === 'chat')
</script>

<style scoped>
.workspace-pane-tab {
  border-radius: 0;
  padding: 0.625rem 0.75rem 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  line-height: 1;
  transition: color 150ms ease, box-shadow 150ms ease, opacity 150ms ease;
}

.workspace-pane-tab:hover {
  color: var(--color-text-main);
}

.workspace-left-content-chat-only {
  width: min(100%, 920px);
  margin-left: auto;
  margin-right: auto;
}
</style>
