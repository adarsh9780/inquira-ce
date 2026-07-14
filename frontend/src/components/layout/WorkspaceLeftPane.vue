<template>
  <div class="flex h-full w-full min-h-0 min-w-0 flex-col" style="background-color: var(--color-workspace-surface);">
    <AppToolbar aria-label="Work pane toolbar">
      <template #start>
        <SegmentedControl v-model="selectedWorkspacePane" :options="workspacePaneOptions" aria-label="Workspace panes" />
      </template>

      <template #end><button
        type="button"
        class="workspace-pane-icon-button"
        :title="commandPaletteTooltip"
        aria-label="Open command palette"
        @click="appStore.openCommandPalette()"
      >
        <MagnifyingGlassIcon class="h-4 w-4" />
      </button>
      
      <!-- Teleport Target for Code/Chat Toolbar -->
      <div id="workspace-left-pane-toolbar" class="min-w-0"></div></template>
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

      <div class="flex-shrink-0 pt-2" style="background-color: var(--color-workspace-surface);">
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
import { shortcutTitle } from '../../utils/keyboardShortcuts'
import {
  ChatBubbleLeftRightIcon,
  CodeBracketIcon,
  MagnifyingGlassIcon,
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
const commandPaletteTooltip = computed(() => shortcutTitle('command-palette', 'Command Palette', typeof navigator !== 'undefined' ? navigator.platform : ''))
</script>

<style scoped>
.workspace-pane-icon-button {
  align-items: center;
  border-radius: var(--radius-md);
  color: var(--color-text-muted);
  display: inline-flex;
  height: 2rem;
  justify-content: center;
  width: 2rem;
  transition:
    background-color var(--motion-duration-fast) var(--motion-ease-standard),
    color var(--motion-duration-fast) var(--motion-ease-standard);
}

.workspace-pane-icon-button:hover {
  background: color-mix(in srgb, var(--color-text-main) 7%, transparent);
  color: var(--color-text-main);
}

</style>
