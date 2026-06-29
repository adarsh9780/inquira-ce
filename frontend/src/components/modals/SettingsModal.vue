<template>
  <Transition
    enter-active-class="dialog-fade-enter-active dialog-pop-enter-active"
    enter-from-class="dialog-fade-enter-from dialog-pop-enter-from"
    leave-active-class="dialog-fade-leave-active dialog-pop-leave-active"
    leave-to-class="dialog-fade-leave-to dialog-pop-leave-to"
  >
    <div
      v-if="modelValue"
      class="fixed inset-0 layer-modal flex items-center justify-center p-4"
    >
      <div class="modal-overlay" @click="closeModal"></div>
      <div
        class="modal-card relative h-[680px] w-full max-w-[900px] text-[var(--color-text-main)]"
        @click.stop
      >
        <button
          type="button"
          class="btn-icon absolute right-3 top-3 z-20"
          aria-label="Close settings"
          @click="closeModal"
        >
          <svg viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="1.8">
            <path d="M6 6l12 12M18 6L6 18" />
          </svg>
        </button>

        <div class="flex h-full">
          <aside class="w-[190px] shrink-0 border-r border-[var(--color-border)] bg-[var(--color-base-soft)] px-3 py-4 flex flex-col justify-between select-none">
            <div class="space-y-0.5">
              <button
                type="button"
                :class="activeSection === 'llm' ? activeNavClass : inactiveNavClass"
                @click="openLeafSection('llm')"
              >
                <KeyIcon class="h-4 w-4 shrink-0" />
                <span>LLM &amp; API Keys</span>
              </button>
              <button
                type="button"
                :class="activeSection === 'workspace' ? activeNavClass : inactiveNavClass"
                @click="openWorkspaceSection"
              >
                <ListBulletIcon class="h-4 w-4 shrink-0" />
                <span>Workspace</span>
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

          <main class="relative flex-1 flex flex-col overflow-hidden">
            <!-- Header Zone -->
            <header class="px-6 py-4 border-b border-[var(--color-border)] bg-[var(--color-base-soft)] shrink-0 select-none">
              <h2 class="text-sm font-bold tracking-tight text-[var(--color-text-main)]">{{ activeSectionTitle }}</h2>
              <p class="text-[11px] text-[var(--color-text-muted)] mt-0.5 leading-snug">{{ activeSectionDescription }}</p>
            </header>

            <div class="relative flex-1 overflow-hidden">
              <section :class="panelClass('llm')" class="scrollbar-hidden absolute inset-0 overflow-y-auto px-6 py-5">
                <LLMSettingsTab @close-request="closeModal" />
              </section>

              <section :class="panelClass('workspace')" class="scrollbar-hidden absolute inset-0 overflow-y-auto px-6 py-5">
                <WorkspaceTab
                  :active-workspace-id="activeWorkspaceId"
                  :workspaces="workspaceItems"
                  @workspace-operation-change="setActiveWorkspaceOperation"
                  @select-workspace="selectWorkspace"
                  @activate-workspace="activateWorkspace"
                  @workspace-created="handleWorkspaceCreated"
                />
              </section>

              <section :class="panelClass('appearance')" class="scrollbar-hidden absolute inset-0 overflow-y-auto px-6 py-5">
                <AppearanceTab />
              </section>



              <section :class="panelClass('account')" class="scrollbar-hidden absolute inset-0 overflow-y-auto px-6 py-5">
                <AccountTab />
              </section>
            </div>
          </main>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useLLMConfig } from '../../composables/useLLMConfig'
import { useAppStore } from '../../stores/appStore'
import { toast } from '../../composables/useToast'
import { filenameFromPath } from '../../utils/pathUtils'
import LLMSettingsTab from './tabs/LLMSettingsTab.vue'
import WorkspaceTab from './tabs/WorkspaceTab.vue'
import AppearanceTab from './tabs/AppearanceTab.vue'
import AccountTab from './tabs/AccountTab.vue'
import {
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
    default: 'llm',
  },
})

const emit = defineEmits(['update:modelValue'])

const appStore = useAppStore()
const llmConfig = useLLMConfig()

const activeSection = ref('llm')
const activeWorkspaceId = ref('')
const currentPanel = ref('llm')
const panelDirection = ref('forward')
const activeWorkspaceOperation = ref('')
const activeWorkspaceOperationMessage = ref('')

const activeNavClass = 'nav-tab-active'
const inactiveNavClass = 'nav-tab'

const activeSectionTitle = computed(() => {
  if (activeSection.value === 'llm') return 'LLM & API Keys'
  if (activeSection.value === 'workspace') return 'Manage Workspaces'
  if (activeSection.value === 'appearance') return 'Appearance Preferences'
  if (activeSection.value === 'account') return 'Account Settings'
  return 'Settings'
})

const activeSectionDescription = computed(() => {
  if (activeSection.value === 'llm') return 'Configure model providers, search credentials, and LLM preferences.'
  if (activeSection.value === 'workspace') return 'Browse, create, configure, activate, or delete your workspaces.'
  if (activeSection.value === 'appearance') return 'Customize application theme presets, typography sizing, and code block fonts.'
  if (activeSection.value === 'account') return 'Manage your user profile configuration and application connection logs.'
  return 'Customize application settings.'
})

const workspaceItems = computed(() => {
  const items = Array.isArray(appStore.workspaces) ? appStore.workspaces : []
  return items.map((workspace) => {
    const duckdbPath = String(workspace?.duckdb_path || '').trim()
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
      await appStore.fetchWorkspaces()
      const initialWorkspace = String(appStore.activeWorkspaceId || '').trim() || String(workspaceItems.value[0]?.id || '').trim()
      activeWorkspaceId.value = initialWorkspace
      initializePanelState(props.initialTab)
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

function normalizeTab(tab) {
  const candidate = String(tab || '').toLowerCase()
  if (candidate === 'api') return 'llm'
  if (candidate === 'data') return 'workspace'
  if (candidate === 'llm' || candidate === 'workspace' || candidate === 'appearance' || candidate === 'account') {
    return candidate
  }
  return 'llm'
}

function initializePanelState(tab) {
  const normalized = normalizeTab(tab)
  if (normalized === 'workspace') {
    activeSection.value = 'workspace'
    currentPanel.value = 'workspace'
    return
  }

  activeSection.value = normalized
  currentPanel.value = normalized
}

function panelClass(panelId) {
  if (currentPanel.value === panelId) {
    return 'translate-x-0 opacity-100 pointer-events-auto settings-panel-transition'
  }
  const offset = panelDirection.value === 'backward' ? '-translate-x-[30px]' : 'translate-x-[30px]'
  return `${offset} opacity-0 pointer-events-none settings-panel-transition`
}

function navigateTo(panel, direction = 'forward') {
  if (notifyWorkspaceOperationBlocked()) return
  panelDirection.value = direction
  currentPanel.value = panel
  if (panel === 'workspace') {
    activeSection.value = 'workspace'
  }
}

function openLeafSection(section) {
  if (notifyWorkspaceOperationBlocked()) return
  activeSection.value = section
  navigateTo(section, 'forward')
}

function openWorkspaceSection() {
  if (notifyWorkspaceOperationBlocked()) return
  activeSection.value = 'workspace'
  navigateTo('workspace', 'forward')
}

function selectWorkspace(workspaceId) {
  if (notifyWorkspaceOperationBlocked()) return
  const nextId = String(workspaceId || '').trim()
  if (!nextId) return
  if (activeWorkspaceId.value !== nextId) {
    activeWorkspaceId.value = nextId
  }
}

async function activateWorkspace(workspaceId) {
  if (notifyWorkspaceOperationBlocked()) return
  const nextId = String(workspaceId || '').trim()
  if (!nextId) return
  activeWorkspaceId.value = nextId
  if (String(appStore.activeWorkspaceId || '').trim() === nextId) return
  await appStore.activateWorkspace(nextId)
}

function handleWorkspaceCreated(payload) {
  const workspaceId = String(payload?.workspaceId || '').trim()
  if (!workspaceId) return
  activeWorkspaceId.value = workspaceId
  activeSection.value = 'workspace'
}

function closeModal() {
  if (notifyWorkspaceOperationBlocked()) return
  emit('update:modelValue', false)
}

function setActiveWorkspaceOperation(payload) {
  if (!payload || payload.locked === false) {
    activeWorkspaceOperation.value = ''
    activeWorkspaceOperationMessage.value = ''
    return
  }
  activeWorkspaceOperation.value = String(payload.operation || 'workspace').trim()
  activeWorkspaceOperationMessage.value = String(payload.message || 'Workspace setup is still running.').trim()
}

function notifyWorkspaceOperationBlocked() {
  if (!activeWorkspaceOperation.value) return false
  if (activeSection.value === 'workspace') {
    return true
  }
  toast.info(
    'Workspace setup in progress',
    activeWorkspaceOperationMessage.value || 'Wait for the current workspace setup step to finish.',
  )
  return true
}
</script>

<style scoped>
.settings-panel-transition {
  transition: transform var(--motion-duration-slow) var(--motion-ease-emphasized),
              opacity var(--motion-duration-slow) var(--motion-ease-standard);
}
</style>
