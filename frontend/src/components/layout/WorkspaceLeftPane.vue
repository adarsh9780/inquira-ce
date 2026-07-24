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
      <div v-if="uiStore.workspacePane === 'code'" class="h-full">
        <CodeTab />
      </div>
      <div v-else class="h-full">
        <ChatTab />
      </div>
      </div>

      <div
        v-if="uiStore.workspacePane === 'chat' && workspaceActivation.workspaceReadiness.ready"
        class="flex-shrink-0 pt-2"
        style="background-color: var(--color-workspace-surface);"
      >
        <ChatInput />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, defineAsyncComponent } from 'vue'
import { useUiStore } from '../../stores/uiStore'
import { usePreferencesStore } from '../../stores/preferencesStore'
import { useArtifactStore } from '../../stores/artifactStore'
import { useExecutionStore } from '../../stores/executionStore'
import { useWorkspaceStore } from '../../stores/workspaceStore'
import { useConversationStore } from '../../stores/conversationStore'
import { useWorkspaceActivation } from '../../composables/useWorkspaceActivation'
import { useArtifactPresentation } from '../../composables/useArtifactPresentation'
import ChatTab from '../chat/ChatTab.vue'
import ChatInput from '../chat/ChatInput.vue'
import AppToolbar from '../ui/AppToolbar.vue'
import SegmentedControl from '../ui/SegmentedControl.vue'
import {
  ChatBubbleLeftRightIcon,
  CodeBracketIcon,
} from '@heroicons/vue/24/outline'

const uiStore = useUiStore()
const preferencesStore = usePreferencesStore()
const artifactStore = useArtifactStore()
const executionStore = useExecutionStore()
const workspaceStore = useWorkspaceStore()
const conversationStore = useConversationStore()
const workspaceActivation = useWorkspaceActivation()
const artifactPresentation = useArtifactPresentation()
const CodeTab = defineAsyncComponent(() => import('../analysis/CodeTab.vue'))
const workspacePaneOptions = [
  { value: 'chat', label: 'Chat', icon: ChatBubbleLeftRightIcon },
  { value: 'code', label: 'Code', icon: CodeBracketIcon },
]
const selectedWorkspacePane = computed({
  get: () => uiStore.workspacePane,
  set: (pane) => uiStore.setWorkspacePane(pane),
})
</script>
