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
      role="dialog"
      aria-modal="true"
      aria-labelledby="settings-modal-title"
      @keydown="handleDialogKeydown"
    >
      <div class="modal-overlay" @click="closeModal"></div>
      <div
        ref="dialogRef"
        class="modal-card settings-modal-card relative h-[min(680px,calc(100dvh-2rem))] w-full max-w-[900px] text-[var(--color-text-main)]"
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

        <div class="settings-modal-layout flex h-full">
          <aside class="settings-modal-nav w-[190px] shrink-0 border-r border-[var(--color-border)] bg-[var(--color-base-soft)] px-3 py-4 flex flex-col justify-between select-none">
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
                <span>Connections</span>
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
              <h2 id="settings-modal-title" class="text-sm font-bold tracking-tight text-[var(--color-text-main)]">{{ activeSectionTitle }}</h2>
              <p class="text-[11px] text-[var(--color-text-muted)] mt-0.5 leading-snug">{{ activeSectionDescription }}</p>
            </header>

            <div class="relative flex-1 overflow-hidden">
              <section :class="panelClass('setup')" :aria-hidden="currentPanel !== 'setup'" :inert="currentPanel !== 'setup'" class="scrollbar-hidden absolute inset-0 overflow-y-auto px-6 py-5">
                <SetupTab />
              </section>

              <section :class="panelClass('connections')" :aria-hidden="currentPanel !== 'connections'" :inert="currentPanel !== 'connections'" class="scrollbar-hidden absolute inset-0 overflow-y-auto px-6 py-5">
                <LLMSettingsTab @close-request="closeModal" />
              </section>

              <section :class="panelClass('workspace')" :aria-hidden="currentPanel !== 'workspace'" :inert="currentPanel !== 'workspace'" class="scrollbar-hidden absolute inset-0 overflow-y-auto px-6 py-5">
                <WorkspaceTab
                  :active-workspace-id="activeWorkspaceId"
                  :workspaces="workspaceItems"
                  @workspace-operation-change="setActiveWorkspaceOperation"
                  @select-workspace="selectWorkspace"
                  @activate-workspace="activateWorkspace"
                  @workspace-created="handleWorkspaceCreated"
                />
              </section>

              <section :class="panelClass('appearance')" :aria-hidden="currentPanel !== 'appearance'" :inert="currentPanel !== 'appearance'" class="scrollbar-hidden absolute inset-0 overflow-y-auto px-6 py-5">
                <AppearanceTab />
              </section>



              <section :class="panelClass('account')" :aria-hidden="currentPanel !== 'account'" :inert="currentPanel !== 'account'" class="scrollbar-hidden absolute inset-0 overflow-y-auto px-6 py-5">
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
import { computed, nextTick, ref, watch } from 'vue'
import { useLLMConfig } from '../../composables/useLLMConfig'
import { useAppStore } from '../../stores/appStore'
import { toast } from '../../composables/useToast'
import { filenameFromPath } from '../../utils/pathUtils'
import LLMSettingsTab from './tabs/LLMSettingsTab.vue'
import WorkspaceTab from './tabs/WorkspaceTab.vue'
import AppearanceTab from './tabs/AppearanceTab.vue'
import AccountTab from './tabs/AccountTab.vue'
import SetupTab from './tabs/SetupTab.vue'
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

const emit = defineEmits(['update:modelValue'])

const appStore = useAppStore()
const llmConfig = useLLMConfig()

const activeSection = ref('setup')
const activeWorkspaceId = ref('')
const currentPanel = ref('setup')
const panelDirection = ref('forward')
const activeWorkspaceOperation = ref('')
const activeWorkspaceOperationMessage = ref('')
const dialogRef = ref(null)
const previouslyFocusedElement = ref(null)

const activeNavClass = 'nav-tab-active'
const inactiveNavClass = 'nav-tab'

const activeSectionTitle = computed(() => {
  if (activeSection.value === 'setup') return 'Setup'
  if (activeSection.value === 'connections') return 'Connections'
  if (activeSection.value === 'workspace') return 'Workspaces'
  if (activeSection.value === 'appearance') return 'Appearance'
  if (activeSection.value === 'account') return 'Account'
  return 'Settings'
})

const activeSectionDescription = computed(() => {
  if (activeSection.value === 'setup') return 'See what is ready and complete the next required step.'
  if (activeSection.value === 'connections') return 'Manage provider credentials shared by every workspace.'
  if (activeSection.value === 'workspace') return 'Manage each workspace, its data, models, privacy, and advanced controls.'
  if (activeSection.value === 'appearance') return 'Choose the theme and typography used throughout Inquira.'
  if (activeSection.value === 'account') return 'Review local profile and application information.'
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
      previouslyFocusedElement.value = document.activeElement instanceof HTMLElement ? document.activeElement : null
      await appStore.fetchWorkspaces()
      const initialWorkspace = String(appStore.activeWorkspaceId || '').trim() || String(workspaceItems.value[0]?.id || '').trim()
      activeWorkspaceId.value = initialWorkspace
      initializePanelState(props.initialTab)
      await nextTick()
      dialogRef.value?.querySelector('button, input, select, textarea, [tabindex]:not([tabindex="-1"])')?.focus?.()
      return
    }
    llmConfig.clearSensitiveState()
    previouslyFocusedElement.value?.focus?.()
    previouslyFocusedElement.value = null
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
  if (candidate === 'api' || candidate === 'llm') return 'connections'
  if (candidate === 'data') return 'workspace'
  if (candidate === 'setup' || candidate === 'connections' || candidate === 'workspace' || candidate === 'appearance' || candidate === 'account') {
    return candidate
  }
  return 'setup'
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
  emit('update:modelValue', false)
}

function closeModal() {
  if (notifyWorkspaceOperationBlocked()) return
  emit('update:modelValue', false)
}

function handleDialogKeydown(event) {
  if (event.key === 'Escape') {
    event.preventDefault()
    closeModal()
    return
  }
  if (event.key !== 'Tab') return
  const focusable = [...(dialogRef.value?.querySelectorAll(
    'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])',
  ) || [])].filter((element) => !element.closest('[inert]'))
  if (!focusable.length) return
  const first = focusable[0]
  const last = focusable[focusable.length - 1]
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
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

@media (max-width: 640px) {
  .settings-modal-card {
    height: calc(100dvh - 1rem);
  }

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
