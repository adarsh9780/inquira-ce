<template>
  <div class="flex h-full w-full min-h-0 min-w-0 flex-col" style="background-color: var(--color-workspace-surface);">
    <div class="workspace-pane-header flex-shrink-0 h-12 px-3 flex items-center gap-3" style="background-color: var(--color-workspace-surface);">
      <div class="workspace-pane-tabs inline-flex items-center gap-1 flex-shrink-0" aria-label="Workspace panes">
        <button
          type="button"
          @click="appStore.setWorkspacePane('code')"
          class="workspace-pane-tab"
          :class="appStore.workspacePane === 'code' ? 'workspace-pane-tab-active' : ''"
          :aria-pressed="appStore.workspacePane === 'code'"
          title="Code"
        >
          <CodeBracketIcon class="h-3.5 w-3.5" />
          <span>Code</span>
        </button>
        <button
          type="button"
          @click="appStore.setWorkspacePane('chat')"
          class="workspace-pane-tab"
          :class="appStore.workspacePane === 'chat' ? 'workspace-pane-tab-active' : ''"
          :aria-pressed="appStore.workspacePane === 'chat'"
          title="Chat"
        >
          <ChatBubbleLeftRightIcon class="h-3.5 w-3.5" />
          <span>Chat</span>
        </button>
        <button
          type="button"
          @click="appStore.setWorkspacePane('ctree')"
          class="workspace-pane-tab"
          :class="appStore.workspacePane === 'ctree' ? 'workspace-pane-tab-active' : ''"
          :aria-pressed="appStore.workspacePane === 'ctree'"
          title="Conversation Tree"
        >
          <ShareIcon class="h-3.5 w-3.5" />
          <span>Tree</span>
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
import {
  ChatBubbleLeftRightIcon,
  CodeBracketIcon,
  ShareIcon,
} from '@heroicons/vue/24/outline'

const appStore = useAppStore()
const isChatOnlyMode = computed(() => appStore.workspacePane === 'chat' && appStore.workspaceLayoutMode === 'chat')
</script>

<style scoped>
.workspace-pane-tab {
  align-items: center;
  border-radius: 0;
  color: var(--color-text-muted);
  display: inline-flex;
  gap: 0.375rem;
  height: 2rem;
  justify-content: center;
  padding: 0 0.625rem;
  position: relative;
  font-size: 0.75rem;
  font-weight: 600;
  line-height: 1;
  transition: color 150ms ease, opacity 150ms ease;
}

.workspace-pane-tab::after {
  background: transparent;
  bottom: -0.5rem;
  content: '';
  height: 2px;
  left: 0.5rem;
  position: absolute;
  right: 0.5rem;
  transition: background-color 150ms ease;
}

.workspace-pane-tab:hover {
  color: var(--color-text-main);
}

.workspace-pane-tab-active {
  color: var(--color-text-main);
}

.workspace-pane-tab-active::after {
  background: var(--color-accent);
}

.workspace-left-content-chat-only {
  width: min(100%, 920px);
  margin-left: auto;
  margin-right: auto;
}
</style>
