<template>
  <section
    class="mx-auto flex h-full w-full max-w-xl flex-col justify-center px-6 py-12"
    data-workspace-readiness-journey
  >
    <p class="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--color-accent-text)]">
      Next step
    </p>
    <h2 class="mt-3 text-2xl font-semibold tracking-[-0.025em] text-[var(--color-text-main)]">
      {{ content.title }}
    </h2>
    <p class="mt-3 max-w-lg text-sm leading-6 text-[var(--color-text-muted)]">
      {{ content.description }}
    </p>

    <div class="mt-8 border-y border-[var(--color-border)] py-4">
      <div class="flex items-center justify-between gap-5">
        <div class="min-w-0">
          <p class="text-sm font-medium text-[var(--color-text-main)]">{{ content.actionLabel }}</p>
          <p class="mt-1 text-xs leading-5 text-[var(--color-text-muted)]">{{ content.actionHint }}</p>
        </div>
        <button
          type="button"
          class="btn-primary shrink-0 px-4 py-2 text-sm"
          data-primary-action
          @click="emit('primary-action')"
        >
          {{ content.actionLabel }}
        </button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'

type ReadinessState =
  | 'no_workspace'
  | 'no_data'
  | 'model_connection_required'
  | 'workspace_configuration_required'

const props = defineProps<{ state: string }>()
const emit = defineEmits<{ 'primary-action': [] }>()

const journeyContent: Record<ReadinessState, {
  title: string
  description: string
  actionLabel: string
  actionHint: string
}> = {
  no_workspace: {
    title: 'Create a workspace',
    description: 'A workspace keeps related data, conversations, code, and results together.',
    actionLabel: 'Create workspace',
    actionHint: 'Name a workspace and make it the home for this analysis.',
  },
  no_data: {
    title: 'Connect your data',
    description: 'Add a local CSV, Parquet, or Excel source to create a refreshable snapshot.',
    actionLabel: 'Add data',
    actionHint: 'Choose a file, review its contents, and select the tables or sheets to use.',
  },
  model_connection_required: {
    title: 'Connect an AI provider',
    description: 'Inquira needs a verified provider before it can answer questions about your data.',
    actionLabel: 'Connect provider',
    actionHint: 'Add or verify the credential shared by your local workspaces.',
  },
  workspace_configuration_required: {
    title: 'Review workspace AI',
    description: 'Confirm the models and data-sharing preference for this workspace.',
    actionLabel: 'Review AI settings',
    actionHint: 'Review the effective models and decide whether bounded samples may be shared.',
  },
}

const content = computed(() => {
  const state = props.state as ReadinessState
  return journeyContent[state] || journeyContent.no_workspace
})
</script>
