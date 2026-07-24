<template>
  <div class="flex h-full min-w-0 rounded-xl overflow-hidden" style="background-color: var(--color-base);">
    <div class="flex-1 min-w-0 flex flex-col">
      <div class="chat-scroll-shell flex-1 min-h-0 overflow-y-auto" style="background-color: var(--color-base);" data-chat-scroll-container>
        <WorkspaceReadinessJourney
          v-if="!workspaceActivation.workspaceReadiness.ready"
          :state="workspaceActivation.workspaceReadiness.state"
          @primary-action="handleReadinessAction"
        />

        <section
          v-else-if="conversationStore.chatHistory.length === 0"
          class="mx-auto flex h-full w-full max-w-2xl flex-col justify-center px-5 py-10"
          aria-labelledby="chat-starter-title"
        >
          <p class="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--color-accent-text)]">Ready</p>
          <h2 id="chat-starter-title" class="mt-3 text-2xl font-semibold tracking-[-0.025em] text-[var(--color-text-main)]">
            Ask about your data
          </h2>
          <p class="mt-2 text-sm leading-6 text-[var(--color-text-muted)]">
            Start with a common analysis, or write your own question below.
          </p>

          <div class="mt-7 divide-y divide-[var(--color-border)] border-y border-[var(--color-border)]">
            <button
              v-for="starter in starterActions"
              :key="starter.prompt"
              type="button"
              class="group flex w-full items-center gap-4 py-3.5 text-left"
              @click="selectStarter(starter.prompt)"
            >
              <span class="min-w-0 flex-1">
                <span class="block text-sm font-medium text-[var(--color-text-main)]">{{ starter.label }}</span>
                <span class="mt-0.5 block text-xs leading-5 text-[var(--color-text-muted)]">{{ starter.description }}</span>
              </span>
              <ArrowRightIcon
                class="h-4 w-4 shrink-0 text-[var(--color-text-muted)] transition-transform duration-200 group-hover:translate-x-0.5 group-hover:text-[var(--color-text-main)]"
                aria-hidden="true"
              />
            </button>
          </div>
        </section>

        <div v-else class="px-2 sm:px-2 pt-2 pb-1 space-y-2">
          <ChatHistory />
        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { useUiStore } from '../../stores/uiStore'
import { usePreferencesStore } from '../../stores/preferencesStore'
import { useArtifactStore } from '../../stores/artifactStore'
import { useExecutionStore } from '../../stores/executionStore'
import { useWorkspaceStore } from '../../stores/workspaceStore'
import { useConversationStore } from '../../stores/conversationStore'
import { useWorkspaceActivation } from '../../composables/useWorkspaceActivation'
import { useArtifactPresentation } from '../../composables/useArtifactPresentation'
import ChatHistory from './ChatHistory.vue'
import WorkspaceReadinessJourney from './WorkspaceReadinessJourney.vue'
import { ArrowRightIcon } from '@heroicons/vue/24/outline'

const uiStore = useUiStore()
const preferencesStore = usePreferencesStore()
const artifactStore = useArtifactStore()
const executionStore = useExecutionStore()
const workspaceStore = useWorkspaceStore()
const conversationStore = useConversationStore()
const workspaceActivation = useWorkspaceActivation()
const artifactPresentation = useArtifactPresentation()

const starterActions = [
  {
    label: 'Summarize this data',
    description: 'Get a concise overview of the shape, measures, and notable patterns.',
    prompt: 'Summarize this dataset',
  },
  {
    label: 'Check data quality',
    description: 'Look for missing values, duplicates, and inconsistent fields.',
    prompt: 'Check for missing values and other data quality issues',
  },
  {
    label: 'Find the main trends',
    description: 'Identify important movements, comparisons, and possible drivers.',
    prompt: 'Show the main trends in this data',
  },
  {
    label: 'Find unusual records',
    description: 'Surface outliers and observations that deserve closer review.',
    prompt: 'Find unusual records and explain why they stand out',
  },
]

function selectStarter(prompt: string) {
  conversationStore.currentQuestion = String(prompt || '')
}

function handleReadinessAction() {
  const state = workspaceActivation.workspaceReadiness.state
  if (state === 'no_workspace') {
    uiStore.openSettings('workspace-general')
    return
  }
  if (state === 'no_data') {
    workspaceActivation.openDataConnectionFlow()
    return
  }
  if (state === 'model_connection_required') {
    uiStore.openSettings('connections')
    return
  }
  if (state === 'workspace_configuration_required') {
    uiStore.openSettings('workspace-ai')
  }
}

onMounted(async () => {
  try {
    await workspaceStore.fetchWorkspaces()
    if (!workspaceStore.activeWorkspaceId) return
    await conversationStore.fetchConversations(workspaceStore.activeWorkspaceId)
    if (!conversationStore.activeConversationId && conversationStore.conversations.length > 0) {
      const firstConversation = conversationStore.conversations[0] as { id?: unknown }
      conversationStore.setActiveConversationId(firstConversation.id)
    }
    if (conversationStore.activeConversationId) {
      await conversationStore.fetchConversationTurns()
    }
  } catch (error) {
    console.error('Failed to initialize workspace conversations:', error)
  }
})

watch(
  () => workspaceStore.activeWorkspaceId,
  async (workspaceId) => {
    if (!workspaceId) return
    await conversationStore.fetchConversations(workspaceId)
    if (conversationStore.activeConversationId) {
      await conversationStore.fetchConversationTurns()
    }
  }
)
</script>

<style scoped>
.chat-scroll-shell {
  scrollbar-width: thin;
  scrollbar-color: color-mix(in srgb, var(--color-border) 68%, transparent) transparent;
}

.chat-scroll-shell::-webkit-scrollbar {
  width: 6px;
}

.chat-scroll-shell::-webkit-scrollbar-track {
  background: transparent;
}

.chat-scroll-shell::-webkit-scrollbar-thumb {
  border-radius: 9999px;
  background: color-mix(in srgb, var(--color-border) 62%, transparent);
}

.chat-scroll-shell::-webkit-scrollbar-thumb:hover {
  background: color-mix(in srgb, var(--color-border) 80%, transparent);
}
</style>
