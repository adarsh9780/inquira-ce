<template>
  <section class="setup-readiness mx-auto max-w-xl">
    <header class="mb-6">
      <p class="text-sm font-semibold text-[var(--color-text-main)]">{{ setupHeadline }}</p>
      <p class="mt-1 text-xs leading-relaxed text-[var(--color-text-muted)]">{{ setupSummary }}</p>
    </header>

    <div class="divide-y divide-[var(--color-border)] border-y border-[var(--color-border)]">
      <div v-for="item in readinessItems" :key="item.key" class="flex items-center gap-3 py-4">
        <span class="flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold" :class="item.complete ? 'bg-[var(--color-success-bg)] text-[var(--color-success)]' : item.current ? 'bg-[var(--color-accent-soft)] text-[var(--color-accent)]' : 'bg-[var(--color-base-soft)] text-[var(--color-text-muted)]'">
          {{ item.complete ? '✓' : item.index }}
        </span>
        <div class="min-w-0 flex-1">
          <p class="text-sm font-medium text-[var(--color-text-main)]">{{ item.label }}</p>
          <p class="mt-0.5 text-xs text-[var(--color-text-muted)]">{{ item.description }}</p>
        </div>
        <button v-if="item.current" type="button" class="btn-primary shrink-0 px-3 py-1.5 text-xs" @click="item.action">{{ item.actionLabel }}</button>
        <span v-else-if="item.complete" class="text-[11px] text-[var(--color-success)]">Complete</span>
      </div>
    </div>

  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useAppStore } from '../../../stores/appStore'
import { modelConnectionService } from '../../../services/modelConnectionService'

const appStore = useAppStore()
const modelConnectionReady = ref(false)

onMounted(async () => {
  try {
    const status = await modelConnectionService.getOnboardingStatus()
    modelConnectionReady.value = Boolean(status?.connection_ready)
  } catch (_error) {
    modelConnectionReady.value = Boolean(
      !appStore.providerRequiresApiKey || appStore.selectedProviderApiKeyPresent,
    )
  }
})

const readinessItems = computed(() => {
  const state = appStore.workspaceReadiness.state
  const hasWorkspace = state !== 'no_workspace'
  const hasData = Number(appStore.activeWorkspaceSummary?.table_count || 0) > 0
  const hasConnection = modelConnectionReady.value
  const configured = Boolean(appStore.workspaceAIConfig?.readiness?.ready)
  const steps = [
    { key: 'connection', label: 'AI provider', description: hasConnection ? 'The application provider is connected.' : 'Connect a provider once for all workspaces.', complete: hasConnection, actionLabel: 'Connect provider', action: () => appStore.openSettings('connections') },
    { key: 'workspace', label: 'Workspace', description: hasWorkspace ? 'An active workspace is selected.' : 'Create a place for your data and conversations.', complete: hasWorkspace, actionLabel: 'Create workspace', action: () => appStore.openSettings('workspace-general') },
    { key: 'configuration', label: 'Workspace AI', description: configured ? 'Models and privacy are configured.' : 'Review workspace models and data-sharing permission.', complete: configured, actionLabel: 'Review', action: () => appStore.openSettings('workspace-ai') },
    { key: 'data', label: 'Data sources', description: hasData ? 'Workspace data is prepared.' : 'Add a local data source to analyze.', complete: hasData, actionLabel: 'Add data', action: () => appStore.openDataConnectionFlow() },
  ]
  const firstIncomplete = steps.findIndex((step) => !step.complete)
  return steps.map((step, index) => ({ ...step, index: index + 1, current: index === firstIncomplete }))
})

const setupHeadline = computed(() => (
  readinessItems.value.every((item) => item.complete)
    ? 'Setup complete'
    : 'Complete your setup'
))

const setupSummary = computed(() => (
  readinessItems.value.every((item) => item.complete)
    ? 'Everything is ready. Close Settings and begin your analysis.'
    : 'Complete the next required step. Finished setup stays out of your way.'
))
</script>
