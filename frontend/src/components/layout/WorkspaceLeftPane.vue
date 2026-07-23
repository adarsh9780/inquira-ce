<template>
  <div class="flex h-full w-full min-h-0 min-w-0 flex-col" style="background-color: var(--color-workspace-surface);">
    <AppToolbar aria-label="Work pane toolbar">
      <template #start>
        <SegmentedControl v-model="selectedWorkspacePane" :options="workspacePaneOptions" aria-label="Workspace panes" />
      </template>

      <template #end>
        <!-- Teleport Target for Code/Chat Toolbar -->
        <div id="workspace-left-pane-toolbar" class="min-w-0"></div>
      </template>
    </AppToolbar>

    <div class="workspace-left-content min-h-0 flex-1 flex flex-col p-2.5 sm:p-3 pb-0">
      <div class="min-h-0 flex-1">
      <div v-show="appStore.workspacePane === 'code'" class="h-full">
        <CodeTab />
      </div>
      <div v-show="appStore.workspacePane === 'chat'" class="h-full">
        <ChatTab />
      </div>
      </div>

      <div
        v-if="appStore.workspacePane === 'chat' && appStore.workspaceReadiness.ready"
        class="flex-shrink-0 pt-2"
        style="background-color: var(--color-workspace-surface);"
      >
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
import AppToolbar from '../ui/AppToolbar.vue'
import SegmentedControl from '../ui/SegmentedControl.vue'
import {
  ChatBubbleLeftRightIcon,
  CodeBracketIcon,
} from '@heroicons/vue/24/outline'

const appStore = useAppStore()
const workspacePaneOptions = [
  { value: 'chat', label: 'Chat', icon: ChatBubbleLeftRightIcon },
  { value: 'code', label: 'Code', icon: CodeBracketIcon },
]
const selectedWorkspacePane = computed({
  get: () => appStore.workspacePane,
  set: (pane) => appStore.setWorkspacePane(pane),
})
</script>
