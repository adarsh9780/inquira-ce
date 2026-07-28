<template>
  <DialogShell
    :open="modelValue"
    title="Settings"
    :description="activeSectionDescription"
    headerless
    content-class="settings-modal-card h-[min(47.5rem,calc(100dvh-2rem))] max-w-[70rem] text-[var(--color-text-main)] max-sm:h-[calc(100dvh-1rem)] max-sm:max-h-[calc(100dvh-1rem)] max-sm:w-[calc(100vw-1rem)] max-sm:rounded-lg"
    @close="closeModal"
  >
    <button
      type="button"
      class="btn-icon absolute right-4 top-4 z-20 max-sm:right-2 max-sm:top-2"
      aria-label="Close settings"
      @click="closeModal"
    >
      <svg viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="1.8">
        <path d="M6 6l12 12M18 6L6 18" />
      </svg>
    </button>

    <div class="settings-modal-layout flex h-full">
      <aside class="settings-modal-nav flex w-44 shrink-0 select-none flex-col justify-between border-r border-[var(--color-border)] bg-[var(--color-base-soft)] px-3 py-4">
        <div class="space-y-0.5">
          <button
            type="button"
            :class="activeSection === 'setup' ? activeNavClass : inactiveNavClass"
            @click="openLeafSection('setup')"
          >
            <CheckCircleIcon class="h-4 w-4 shrink-0" />
            <span>Setup</span>
          </button>
          <button
            type="button"
            :class="activeSection === 'workspace' ? activeNavClass : inactiveNavClass"
            @click="openWorkspaceSection"
          >
            <ListBulletIcon class="h-4 w-4 shrink-0" />
            <span>Workspaces</span>
          </button>
          <button
            type="button"
            :class="activeSection === 'connections' ? activeNavClass : inactiveNavClass"
            @click="openLeafSection('connections')"
          >
            <KeyIcon class="h-4 w-4 shrink-0" />
            <span>AI providers</span>
          </button>
          <button
            type="button"
            :class="activeSection === 'appearance' ? activeNavClass : inactiveNavClass"
            @click="openLeafSection('appearance')"
          >
            <PaintBrushIcon class="h-4 w-4 shrink-0" />
            <span>Appearance</span>
          </button>
          <button
            type="button"
            :class="activeSection === 'account' ? activeNavClass : inactiveNavClass"
            @click="openLeafSection('account')"
          >
            <UserIcon class="h-4 w-4 shrink-0" />
            <span>Account</span>
          </button>
        </div>
      </aside>

      <main class="relative flex flex-1 flex-col overflow-hidden">
        <header class="shrink-0 select-none border-b border-[var(--color-border)] bg-[var(--color-base-soft)] px-6 py-4 max-sm:px-4 max-sm:py-3">
          <h2 id="settings-modal-title" class="text-sm font-semibold leading-tight tracking-tight text-[var(--color-text-main)]">
            {{ activeSectionTitle }}
          </h2>
          <p class="mt-1 pr-10 text-xs leading-5 text-[var(--color-text-muted)]">
            {{ activeSectionDescription }}
          </p>
        </header>

        <div class="relative flex-1 overflow-hidden">
          <section v-if="currentPanel === 'setup'" :class="panelClass('setup')" class="scrollbar-hidden absolute inset-0 overflow-y-auto px-6 py-5 max-sm:px-4 max-sm:py-4">
            <SetupTab />
          </section>

          <section v-if="currentPanel === 'connections'" :class="panelClass('connections')" class="scrollbar-hidden absolute inset-0 overflow-y-auto px-6 py-5 max-sm:px-4 max-sm:py-4">
            <LLMSettingsTab @close-request="closeModal" />
          </section>

          <section v-if="currentPanel === 'workspace'" :class="panelClass('workspace')" class="scrollbar-hidden absolute inset-0 overflow-y-auto px-6 py-5 max-sm:px-4 max-sm:py-4">
            <WorkspaceTab
              :active-workspace-id="activeWorkspaceId"
              :initial-section="workspaceInitialSection"
              :workspaces="workspaceItems"
              @select-workspace="selectWorkspace"
              @activate-workspace="activateWorkspace"
              @workspace-created="handleWorkspaceCreated"
              @workspace-setup-complete="handleWorkspaceSetupComplete"
            />
          </section>

          <section v-if="currentPanel === 'appearance'" :class="panelClass('appearance')" class="scrollbar-hidden absolute inset-0 overflow-y-auto px-6 py-5 max-sm:px-4 max-sm:py-4">
            <AppearanceTab />
          </section>

          <section v-if="currentPanel === 'account'" :class="panelClass('account')" class="scrollbar-hidden absolute inset-0 overflow-y-auto px-6 py-5 max-sm:px-4 max-sm:py-4">
            <AccountTab />
          </section>
        </div>
      </main>
    </div>
  </DialogShell>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, ref, watch } from 'vue'
import { useLLMConfig } from '../../composables/useLLMConfig'
import { useUiStore } from '../../stores/uiStore'
import { usePreferencesStore } from '../../stores/preferencesStore'
import { useArtifactStore } from '../../stores/artifactStore'
import { useExecutionStore } from '../../stores/executionStore'
import { useWorkspaceStore } from '../../stores/workspaceStore'
import { useConversationStore } from '../../stores/conversationStore'
import { useWorkspaceActivation } from '../../composables/useWorkspaceActivation'
import { useArtifactPresentation } from '../../composables/useArtifactPresentation'
import { filenameFromPath } from '../../utils/pathUtils'
import { DialogShell } from '../ui/dialog'
import {
  CheckCircleIcon,
  ListBulletIcon,
  KeyIcon,
  PaintBrushIcon,
  UserIcon,
} from '@heroicons/vue/24/outline'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  initialTab: {
    type: String,
    default: 'setup',
  },
})

const SetupTab = defineAsyncComponent(() => import('./tabs/SetupTab.vue'))
const LLMSettingsTab = defineAsyncComponent(() => import('./tabs/LLMSettingsTab.vue'))
const WorkspaceTab = defineAsyncComponent(() => import('./tabs/WorkspaceTab.vue'))
const AppearanceTab = defineAsyncComponent(() => import('./tabs/AppearanceTab.vue'))
const AccountTab = defineAsyncComponent(() => import('./tabs/AccountTab.vue'))

const emit = defineEmits(['update:modelValue'])

const uiStore = useUiStore()
const preferencesStore = usePreferencesStore()
const artifactStore = useArtifactStore()
const executionStore = useExecutionStore()
const workspaceStore = useWorkspaceStore()
const conversationStore = useConversationStore()
const workspaceActivation = useWorkspaceActivation()
const artifactPresentation = useArtifactPresentation()
const llmConfig = useLLMConfig()

const activeSection = ref('setup')
const activeWorkspaceId = ref('')
const workspaceInitialSection = ref('general')
const currentPanel = ref('setup')
const panelDirection = ref('forward')

const activeNavClass = 'nav-tab-active'
const inactiveNavClass = 'nav-tab'

const activeSectionTitle = computed(() => {
  if (activeSection.value === 'setup') return 'Setup'
  if (activeSection.value === 'connections') return 'AI providers'
  if (activeSection.value === 'workspace') return 'Workspaces'
  if (activeSection.value === 'appearance') return 'Appearance'
  if (activeSection.value === 'account') return 'Account'
  return 'Settings'
})

const activeSectionDescription = computed(() => {
  if (activeSection.value === 'setup') return 'See what is ready and complete the next required step.'
  if (activeSection.value === 'connections') return 'Manage AI provider credentials shared by every workspace.'
  if (activeSection.value === 'workspace') return 'Manage each workspace, its data, models, privacy, and advanced controls.'
  if (activeSection.value === 'appearance') return 'Choose the theme and typography used throughout Inquira.'
  if (activeSection.value === 'account') return 'Review local profile and application information.'
  return 'Customize application settings.'
})

const workspaceItems = computed(() => {
  const items = Array.isArray(workspaceStore.workspaces) ? workspaceStore.workspaces : []
  return items.map((workspace) => {
    const duckdbPath = String((workspace as { duckdb_path?: unknown }).duckdb_path || '').trim()
    const filename = filenameFromPath(duckdbPath, 'workspace.duckdb')
    return {
      ...workspace,
      filename,
    }
  })
})

watch(
  () => props.modelValue,
  async (isOpen) => {
    if (isOpen) {
      initializePanelState(props.initialTab)
      await workspaceStore.fetchWorkspaces()
      const initialWorkspace = String(workspaceStore.activeWorkspaceId || '').trim() || String(workspaceItems.value[0]?.id || '').trim()
      activeWorkspaceId.value = initialWorkspace
      return
    }
    llmConfig.clearSensitiveState()
  },
  { immediate: true },
)

watch(
  () => props.initialTab,
  (tab) => {
    if (!props.modelValue) return
    initializePanelState(tab)
  },
)

function normalizeTab(tab: unknown): string {
  const candidate = String(tab || '').toLowerCase()
  if (candidate === 'api' || candidate === 'llm') return 'connections'
  if (candidate === 'data' || candidate === 'models' || candidate.startsWith('workspace-')) return 'workspace'
  if (candidate === 'setup' || candidate === 'connections' || candidate === 'workspace' || candidate === 'appearance' || candidate === 'account') {
    return candidate
  }
  return 'setup'
}

function initializePanelState(tab: unknown): void {
  const candidate = String(tab || '').trim().toLowerCase()
  workspaceInitialSection.value = candidate === 'data' || candidate === 'workspace-data'
    ? 'data'
    : candidate === 'models' || candidate === 'workspace-ai'
      ? 'ai'
      : 'general'
  const normalized = normalizeTab(tab)
  if (normalized === 'workspace') {
    activeSection.value = 'workspace'
    currentPanel.value = 'workspace'
    return
  }

  activeSection.value = normalized
  currentPanel.value = normalized
}

function panelClass(panelId: string): string {
  if (currentPanel.value === panelId) {
    return 'translate-x-0 opacity-100 pointer-events-auto settings-panel-transition'
  }
  const offset = panelDirection.value === 'backward' ? '-translate-x-8' : 'translate-x-8'
  return `${offset} opacity-0 pointer-events-none settings-panel-transition`
}

function navigateTo(panel: string, direction = 'forward'): void {
  panelDirection.value = direction
  currentPanel.value = panel
  if (panel === 'workspace') {
    activeSection.value = 'workspace'
  }
}

function openLeafSection(section: string): void {
  activeSection.value = section
  navigateTo(section, 'forward')
}

function openWorkspaceSection() {
  activeSection.value = 'workspace'
  navigateTo('workspace', 'forward')
}

function selectWorkspace(workspaceId: unknown): void {
  const nextId = String(workspaceId || '').trim()
  if (!nextId) return
  if (activeWorkspaceId.value !== nextId) {
    activeWorkspaceId.value = nextId
  }
}

async function activateWorkspace(workspaceId: unknown) {
  const nextId = String(workspaceId || '').trim()
  if (!nextId) return
  activeWorkspaceId.value = nextId
  if (String(workspaceStore.activeWorkspaceId || '').trim() === nextId) return
  await workspaceActivation.activateWorkspace(nextId)
}

function handleWorkspaceCreated(payload: { workspaceId?: unknown }) {
  const workspaceId = String(payload?.workspaceId || '').trim()
  if (!workspaceId) return
  activeWorkspaceId.value = workspaceId
  activeSection.value = 'workspace'
  workspaceInitialSection.value = 'ai'
}

function handleWorkspaceSetupComplete(payload: { workspaceId?: unknown }) {
  const workspaceId = String(payload?.workspaceId || '').trim()
  if (workspaceId) activeWorkspaceId.value = workspaceId
  emit('update:modelValue', false)
}

function closeModal() {
  emit('update:modelValue', false)
}

</script>

<style scoped>
.settings-panel-transition {
  transition: transform var(--motion-duration-slow) var(--motion-ease-emphasized),
              opacity var(--motion-duration-slow) var(--motion-ease-standard);
}

@media (max-width: 640px) {
  .settings-modal-layout {
    flex-direction: column;
  }

  .settings-modal-nav {
    width: 100%;
    border-right: 0;
    border-bottom: 1px solid var(--color-border);
    padding: 0.5rem 2.75rem 0.5rem 0.5rem;
  }

  .settings-modal-nav > div {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
