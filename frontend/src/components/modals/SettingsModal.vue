<template>
  <Transition
    enter-active-class="transition duration-200"
    enter-from-class="opacity-0"
    leave-active-class="transition duration-150"
    leave-to-class="opacity-0"
  >
    <div
      v-if="modelValue"
      class="fixed inset-0 z-[80] flex items-center justify-center bg-black/40 p-4"
      @click="closeModal"
    >
      <div
        class="relative h-[680px] w-full max-w-[980px] overflow-hidden rounded-xl border border-[var(--color-border-strong)] bg-[var(--color-base)] text-[var(--color-text-main)] shadow-2xl"
        @click.stop
      >
        <button
          type="button"
          class="absolute right-3 top-3 z-20 rounded-md p-1 text-[var(--color-text-muted)] hover:bg-[var(--color-base-soft)] hover:text-[var(--color-text-main)]"
          aria-label="Close settings"
          @click="closeModal"
        >
          <svg viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="1.8">
            <path d="M6 6l12 12M18 6L6 18" />
          </svg>
        </button>

        <div class="flex h-full">
          <aside class="relative w-[190px] overflow-hidden border-r border-[var(--color-border)] bg-[var(--color-base-soft)]">
            <section
              class="absolute inset-0 px-3 py-4 transition-transform duration-[220ms]"
              :style="{ transform: navLevel === 1 ? 'translateX(0%)' : 'translateX(-100%)', transitionTimingFunction: 'cubic-bezier(0.4,0,0.2,1)' }"
            >
              <p class="mb-3 px-2 text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">Settings</p>

              <button
                type="button"
                class="mb-1 flex w-full items-center justify-between rounded-lg px-2.5 py-2 text-sm transition-all"
                :class="activeSection === 'llm' ? activeNavClass : inactiveNavClass"
                @click="openLeafSection('llm')"
              >
                <span>LLM &amp; API Keys</span>
              </button>

              <button
                type="button"
                class="mb-1 flex w-full items-center justify-between rounded-lg px-2.5 py-2 text-sm transition-all"
                :class="activeSection === 'workspace' ? activeNavClass : inactiveNavClass"
                @click="openWorkspaceLevel"
              >
                <span>Workspace</span>
                <span class="text-xs">›</span>
              </button>

              <button
                type="button"
                class="mb-1 flex w-full items-center justify-between rounded-lg px-2.5 py-2 text-sm transition-all"
                :class="activeSection === 'account' ? activeNavClass : inactiveNavClass"
                @click="openLeafSection('account')"
              >
                <span>Account</span>
              </button>
            </section>

            <section
              class="absolute inset-0 px-3 py-4 transition-transform duration-[220ms]"
              :style="{ transform: navLevel === 2 ? 'translateX(0%)' : 'translateX(100%)', transitionTimingFunction: 'cubic-bezier(0.4,0,0.2,1)' }"
            >
              <button
                type="button"
                class="mb-3 inline-flex items-center gap-1 text-sm text-[var(--color-accent)] hover:brightness-90"
                @click="closeWorkspaceLevel"
              >
                <svg viewBox="0 0 20 20" class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="1.8">
                  <path d="M12 5l-5 5 5 5" />
                </svg>
                <span>Back</span>
              </button>
              <p class="mb-2 px-2 text-[11px] font-medium uppercase tracking-wider text-[var(--color-text-muted)]">Workspaces</p>

              <div class="space-y-1">
                <button
                  v-for="workspace in workspaceItems"
                  :key="workspace.id"
                  type="button"
                  class="flex w-full items-start justify-between rounded-lg px-2.5 py-2 text-left transition-all"
                  :class="workspace.id === activeWorkspaceId ? activeNavClass : inactiveNavClass"
                  @click="handleWorkspaceNavSelect(workspace.id)"
                >
                  <span class="min-w-0">
                    <span class="block truncate text-sm">{{ workspace.name || 'Untitled workspace' }}</span>
                    <span class="block truncate text-xs text-[var(--color-text-muted)]">{{ workspace.filename }}</span>
                  </span>
                  <span class="ml-2 pt-1">
                    <span
                      v-if="workspace.id === activeWorkspaceId"
                      class="mt-1 block h-2 w-2 rounded-full bg-[var(--color-success)]"
                    ></span>
                    <span v-else class="text-xs text-[var(--color-text-muted)]">›</span>
                  </span>
                </button>
              </div>
            </section>
          </aside>

          <main class="relative flex-1 overflow-hidden">
            <section :class="panelClass('llm')" class="absolute inset-0 overflow-y-auto px-5 py-5">
              <LLMSettingsTab @close-request="closeModal" />
            </section>

            <section :class="panelClass('ws-list')" class="absolute inset-0 overflow-y-auto px-5 py-5">
              <WorkspaceTab
                panel-mode="ws-list"
                :active-workspace-id="activeWorkspaceId"
                :workspaces="workspaceItems"
                @navigate="navigateTo"
                @set-active-workspace="setActiveWorkspace"
              />
            </section>

            <section :class="panelClass('ws-detail')" class="absolute inset-0 overflow-y-auto px-5 py-5">
              <WorkspaceTab
                panel-mode="ws-detail"
                :active-workspace-id="activeWorkspaceId"
                :workspaces="workspaceItems"
                @navigate="navigateTo"
                @set-active-workspace="setActiveWorkspace"
              />
            </section>

            <section :class="panelClass('ws-create')" class="absolute inset-0 overflow-y-auto px-5 py-5">
              <WorkspaceTab
                panel-mode="ws-create"
                :active-workspace-id="activeWorkspaceId"
                :workspaces="workspaceItems"
                @navigate="navigateTo"
                @set-active-workspace="setActiveWorkspace"
              />
            </section>

            <section :class="panelClass('account')" class="absolute inset-0 overflow-y-auto px-5 py-5">
              <AccountTab />
            </section>
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
import LLMSettingsTab from './tabs/LLMSettingsTab.vue'
import WorkspaceTab from './tabs/WorkspaceTab.vue'
import AccountTab from './tabs/AccountTab.vue'

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

const navLevel = ref(1)
const activeSection = ref('llm')
const activeWorkspaceId = ref('')
const currentPanel = ref('llm')
const panelDirection = ref('forward')

const activeNavClass = 'bg-[var(--color-accent-soft)] text-[var(--color-accent)] font-medium'
const inactiveNavClass = 'text-[var(--color-text-main)] hover:bg-[var(--color-base)]'

const workspaceItems = computed(() => {
  const items = Array.isArray(appStore.workspaces) ? appStore.workspaces : []
  return items.map((workspace) => {
    const duckdbPath = String(workspace?.duckdb_path || '').trim()
    const filename = duckdbPath.split('/').pop() || 'workspace.duckdb'
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
  if (candidate === 'llm' || candidate === 'workspace' || candidate === 'account') return candidate
  return 'llm'
}

function initializePanelState(tab) {
  const normalized = normalizeTab(tab)
  if (normalized === 'workspace') {
    activeSection.value = 'workspace'
    navLevel.value = 2
    currentPanel.value = 'ws-list'
    return
  }

  navLevel.value = 1
  activeSection.value = normalized
  currentPanel.value = normalized === 'account' ? 'account' : 'llm'
}

function panelClass(panelId) {
  if (currentPanel.value === panelId) {
    return 'translate-x-0 opacity-100 pointer-events-auto transition-all duration-200 ease-in-out'
  }
  const offset = panelDirection.value === 'backward' ? '-translate-x-[30px]' : 'translate-x-[30px]'
  return `${offset} opacity-0 pointer-events-none transition-all duration-200 ease-in-out`
}

function navigateTo(panel, direction = 'forward') {
  panelDirection.value = direction
  currentPanel.value = panel
  if (panel.startsWith('ws-')) {
    activeSection.value = 'workspace'
    navLevel.value = 2
  }
}

function openLeafSection(section) {
  navLevel.value = 1
  activeSection.value = section
  navigateTo(section === 'account' ? 'account' : 'llm', 'forward')
}

function openWorkspaceLevel() {
  activeSection.value = 'workspace'
  navLevel.value = 2
  navigateTo('ws-list', 'forward')
}

function closeWorkspaceLevel() {
  navLevel.value = 1
  panelDirection.value = 'backward'
  activeSection.value = 'workspace'
}

async function handleWorkspaceNavSelect(workspaceId) {
  await setActiveWorkspace(workspaceId)
  navigateTo('ws-detail', 'forward')
}

async function setActiveWorkspace(workspaceId) {
  const nextId = String(workspaceId || '').trim()
  if (!nextId) return
  if (activeWorkspaceId.value !== nextId) {
    activeWorkspaceId.value = nextId
  }
  if (String(appStore.activeWorkspaceId || '').trim() !== nextId) {
    await appStore.activateWorkspace(nextId)
  }
}

function closeModal() {
  emit('update:modelValue', false)
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Ubuntu:wght@300;400;500;700&display=swap');

:global(body),
:global(button),
:global(input),
:global(select),
:global(textarea) {
  font-family: 'Ubuntu', sans-serif;
  font-weight: 400;
}
</style>
