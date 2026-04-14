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
        class="relative h-[680px] w-full max-w-[900px] overflow-hidden rounded-xl border border-[var(--color-border-strong)] bg-[var(--color-base)] text-[var(--color-text-main)] shadow-2xl"
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
          <aside class="w-[190px] border-r border-[var(--color-border)] bg-[var(--color-base-soft)] px-3 py-4">
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
              @click="openWorkspaceSection"
            >
              <span>Workspace</span>
            </button>

            <button
              type="button"
              class="mb-1 flex w-full items-center justify-between rounded-lg px-2.5 py-2 text-sm transition-all"
              :class="activeSection === 'account' ? activeNavClass : inactiveNavClass"
              @click="openLeafSection('account')"
            >
              <span>Account</span>
            </button>
          </aside>

          <main class="relative flex-1 overflow-hidden">
            <section :class="panelClass('llm')" class="absolute inset-0 overflow-y-auto px-5 py-5">
              <LLMSettingsTab @close-request="closeModal" />
            </section>

            <section :class="panelClass('ws-list')" class="absolute inset-0 overflow-y-auto px-5 pb-5 pt-10">
              <WorkspaceTab
                panel-mode="ws-list"
                :active-workspace-id="activeWorkspaceId"
                :workspaces="workspaceItems"
                @navigate="navigateTo"
                @set-active-workspace="setActiveWorkspace"
              />
            </section>

            <section :class="panelClass('ws-detail')" class="absolute inset-0 overflow-y-auto px-5 pb-5 pt-10">
              <WorkspaceTab
                panel-mode="ws-detail"
                :active-workspace-id="activeWorkspaceId"
                :workspaces="workspaceItems"
                @navigate="navigateTo"
                @set-active-workspace="setActiveWorkspace"
              />
            </section>

            <section :class="panelClass('ws-create')" class="absolute inset-0 overflow-y-auto px-5 pb-5 pt-10">
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
    currentPanel.value = 'ws-list'
    return
  }

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
  }
}

function openLeafSection(section) {
  activeSection.value = section
  navigateTo(section === 'account' ? 'account' : 'llm', 'forward')
}

function openWorkspaceSection() {
  activeSection.value = 'workspace'
  navigateTo('ws-list', 'forward')
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
