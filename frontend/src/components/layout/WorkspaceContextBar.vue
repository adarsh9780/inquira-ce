<template>
  <header
    data-workspace-context-bar
    class="workspace-context-bar relative z-30 flex h-12 shrink-0 items-center gap-2 border-b px-2.5 sm:gap-3 sm:px-3"
  >
    <div class="flex min-w-0 flex-1 items-center gap-2">
      <div class="min-w-0">
        <div class="flex min-w-0 items-center gap-1.5 text-[13px]">
          <span class="truncate font-semibold text-[var(--color-text-main)]">
            {{ activeWorkspaceName }}
          </span>
          <ChevronRightIcon class="h-3 w-3 shrink-0 text-[var(--color-text-muted)] opacity-60" aria-hidden="true" />
          <span class="truncate text-xs text-[var(--color-text-muted)]">
            {{ activeConversationTitle }}
          </span>
        </div>
      </div>

      <div
        v-if="appStore.hasWorkspace"
        data-workspace-status
        class="hidden shrink-0 items-center gap-1.5 lg:flex"
      >
        <span
          class="context-state-chip"
          :class="runtimeStateClass"
          :title="`Runtime: ${runtimeStateLabel}`"
        >
          <span class="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true"></span>
          {{ runtimeStateLabel }}
        </span>
        <span
          class="context-state-chip text-[var(--color-text-muted)]"
          :title="dataStateLabel"
        >
          <CircleStackIcon class="h-3 w-3" aria-hidden="true" />
          {{ dataStateLabel }}
        </span>
      </div>
    </div>

    <div class="flex shrink-0 items-center gap-1.5">
      <button
        type="button"
        data-action="add-data"
        class="context-add-data-button"
        :title="appStore.hasWorkspace ? 'Add a data source' : 'Create a workspace'"
        :aria-label="appStore.hasWorkspace ? 'Add a data source' : 'Create a workspace'"
        @click="appStore.openDataConnectionFlow()"
      >
        <PlusIcon class="h-3.5 w-3.5" aria-hidden="true" />
        <span class="hidden sm:inline">{{ appStore.hasWorkspace ? 'Add data' : 'New workspace' }}</span>
      </button>

      <div
        v-if="appStore.activeTurnId"
        class="context-turn-controls hidden items-center sm:flex"
        role="group"
        aria-label="Turn navigation"
      >
        <button
          type="button"
          data-action="previous-turn"
          class="context-icon-button"
          title="Previous turn"
          aria-label="Previous turn"
          :disabled="!appStore.activeTurnRelations?.previous_turn"
          @click="appStore.goToPreviousTurn()"
        >
          <ChevronLeftIcon class="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          data-action="next-turn"
          class="context-icon-button"
          title="Next turn"
          aria-label="Next turn"
          :disabled="!appStore.activeTurnRelations?.next_turn"
          @click="appStore.goToNextTurn()"
        >
          <ChevronRightIcon class="h-3.5 w-3.5" />
        </button>
      </div>

      <div v-if="appStore.hasWorkspace" class="workspace-context-model hidden w-36 min-w-0 md:block xl:w-44">
        <ModelSelector
          :selected-model="effectiveWorkspaceModel"
          :model-options="workspaceModelOptions"
          :provider="effectiveWorkspaceProvider"
          :backend-search="searchProviderModels"
          :search-loading="appStore.providerModelSearchLoading"
          :search-debounce-ms="250"
          :max-options-without-search="10"
          @model-changed="handleModelChange"
          @manage-models="appStore.openSettings('workspace-ai')"
        />
      </div>

      <button
        type="button"
        class="context-icon-button"
        title="Open command palette"
        aria-label="Open command palette"
        @click="appStore.openCommandPalette()"
      >
        <MagnifyingGlassIcon class="h-4 w-4" />
      </button>
      <button
        type="button"
        class="context-icon-button"
        title="Workspace settings"
        aria-label="Open workspace settings"
        @click="appStore.openSettings('workspace')"
      >
        <Cog6ToothIcon class="h-4 w-4" />
      </button>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  CircleStackIcon,
  Cog6ToothIcon,
  MagnifyingGlassIcon,
  PlusIcon,
} from '@heroicons/vue/24/outline'
import { useAppStore } from '../../stores/appStore'
import { preferencesApi } from '../../api/preferences'
import ModelSelector from '../ui/ModelSelector.vue'

const appStore = useAppStore()

const activeWorkspaceName = computed(() => {
  const workspaceId = String(appStore.activeWorkspaceId || '').trim()
  if (!workspaceId) return 'No workspace'
  const workspace = appStore.workspaces.find((item) => String(item?.id || '').trim() === workspaceId)
  return String(workspace?.name || '').trim() || 'Untitled workspace'
})

const activeConversationTitle = computed(() => {
  const conversationId = String(appStore.activeConversationId || '').trim()
  if (!conversationId) return 'New conversation'
  const conversation = appStore.conversations.find((item) => String(item?.id || '').trim() === conversationId)
  return String(conversation?.title || '').trim() || 'Untitled conversation'
})

const runtimeStateLabel = computed(() => {
  switch (String(appStore.activeWorkspaceRuntimeStatus || 'missing')) {
    case 'ready': return 'Runtime ready'
    case 'busy': return 'Working'
    case 'starting':
    case 'connecting': return 'Starting runtime'
    case 'error': return 'Runtime issue'
    default: return 'Runtime idle'
  }
})

const runtimeStateClass = computed(() => {
  switch (String(appStore.activeWorkspaceRuntimeStatus || 'missing')) {
    case 'ready': return 'text-[var(--color-success)]'
    case 'busy': return 'text-[var(--color-warning)]'
    case 'starting':
    case 'connecting': return 'text-[var(--color-accent)]'
    case 'error': return 'text-[var(--color-error)]'
    default: return 'text-[var(--color-text-muted)]'
  }
})

const workspaceTableCount = computed(() => Math.max(
  0,
  Number(appStore.activeWorkspaceSummary?.table_count || 0),
))
const dataStateLabel = computed(() => {
  const count = workspaceTableCount.value
  if (count > 0) return `${count} table${count === 1 ? '' : 's'}`
  return 'No data'
})

const effectiveWorkspaceProvider = computed(() => (
  appStore.workspaceAIConfig?.effective?.provider || appStore.llmProvider
))
const effectiveWorkspaceModel = computed(() => (
  appStore.workspaceAIConfig?.effective?.main_model || appStore.selectedModel
))
const workspaceModelOptions = computed(() => {
  const configured = appStore.workspaceAIConfig?.defaults?.provider === effectiveWorkspaceProvider.value
    ? appStore.availableModels
    : []
  const values = Array.isArray(configured) ? [...configured] : []
  if (effectiveWorkspaceModel.value && !values.includes(effectiveWorkspaceModel.value)) {
    values.unshift(effectiveWorkspaceModel.value)
  }
  return values
})

async function handleModelChange(model) {
  const config = appStore.workspaceAIConfig
  if (!config || !appStore.activeWorkspaceId) {
    appStore.setSelectedModel(model)
    return
  }
  const overrides = config.overrides || {}
  await appStore.saveWorkspaceAIConfig({
    llm_provider_override: overrides.provider,
    main_model_override: model,
    lite_model_override: overrides.lite_model,
    coding_model_override: overrides.coding_model,
    llm_temperature_override: overrides.temperature,
    llm_max_tokens_override: overrides.max_tokens,
    llm_top_p_override: overrides.top_p,
    allow_llm_data_samples: Boolean(overrides.allow_llm_data_samples),
  })
}

async function searchProviderModels(query, limit = 25) {
  const response = await preferencesApi.searchModels(
    effectiveWorkspaceProvider.value,
    query,
    limit,
  )
  return Array.isArray(response?.models) ? response.models : []
}
</script>

<style scoped>
.workspace-context-bar {
  background:
    linear-gradient(
      180deg,
      color-mix(in srgb, var(--color-workspace-surface) 97%, var(--color-text-main)),
      var(--color-workspace-surface)
    );
  border-color: var(--color-border);
}

.context-state-chip {
  align-items: center;
  background: color-mix(in srgb, var(--color-panel-muted) 72%, transparent);
  border: 1px solid color-mix(in srgb, currentColor 16%, var(--color-border));
  border-radius: 999px;
  display: inline-flex;
  font-size: 0.6875rem;
  font-weight: 600;
  gap: 0.3rem;
  height: 1.5rem;
  letter-spacing: 0.01em;
  padding: 0 0.45rem;
}

.context-add-data-button {
  align-items: center;
  background: var(--color-text-main);
  border: 1px solid var(--color-text-main);
  border-radius: var(--radius-md);
  color: var(--color-workspace-surface);
  display: inline-flex;
  font-size: 0.75rem;
  font-weight: 700;
  gap: 0.3rem;
  height: 1.875rem;
  padding: 0 0.55rem;
  transition:
    opacity var(--motion-duration-fast) var(--motion-ease-standard),
    transform var(--motion-duration-fast) var(--motion-ease-standard);
}

.context-add-data-button:hover {
  opacity: 0.86;
}

.context-add-data-button:active {
  transform: translateY(1px);
}

.context-icon-button {
  align-items: center;
  border-radius: var(--radius-md);
  color: var(--color-text-muted);
  display: inline-flex;
  height: 1.75rem;
  justify-content: center;
  transition:
    background-color var(--motion-duration-fast) var(--motion-ease-standard),
    color var(--motion-duration-fast) var(--motion-ease-standard);
  width: 1.75rem;
}

.context-icon-button:hover:not(:disabled) {
  background: var(--color-panel-muted);
  color: var(--color-text-main);
}

.context-icon-button:disabled {
  cursor: default;
  opacity: 0.32;
}

.context-turn-controls {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.context-turn-controls .context-icon-button + .context-icon-button {
  border-left: 1px solid var(--color-border);
}

.workspace-context-model :deep([role='listbox']) {
  bottom: auto !important;
  margin-bottom: 0 !important;
  margin-top: 0.5rem !important;
  top: 100% !important;
}

@media (prefers-reduced-motion: reduce) {
  .context-add-data-button,
  .context-icon-button {
    transition: none;
  }
}
</style>
