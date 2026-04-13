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
        class="relative w-full max-w-[560px] rounded-xl border border-[var(--color-border-strong)] bg-[var(--color-base)] text-[var(--color-text-main)] shadow-2xl"
        @click.stop
      >
        <div class="flex items-center justify-between border-b border-[var(--color-border)] px-4 pt-2">
          <div class="flex items-center gap-1">
            <button
              type="button"
              class="inline-flex items-center gap-2 border-b-2 px-3 py-2 text-sm font-medium transition-all"
              :class="activeTab === 'llm'
                ? 'border-[var(--color-accent)] text-[var(--color-accent)]'
                : 'border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text-main)]'"
              @click="activeTab = 'llm'"
            >
              <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8">
                <path d="M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z" />
                <path d="M8.5 10.5h7M8.5 13.5h4" />
              </svg>
              <span>LLM &amp; API Keys</span>
            </button>

            <button
              type="button"
              class="inline-flex items-center gap-2 border-b-2 px-3 py-2 text-sm font-medium transition-all"
              :class="activeTab === 'workspace'
                ? 'border-[var(--color-accent)] text-[var(--color-accent)]'
                : 'border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text-main)]'"
              @click="activeTab = 'workspace'"
            >
              <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8">
                <path d="M3 7h6l2 2h10v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z" />
              </svg>
              <span>Workspace</span>
            </button>

            <button
              type="button"
              class="inline-flex items-center gap-2 border-b-2 px-3 py-2 text-sm font-medium transition-all"
              :class="activeTab === 'account'
                ? 'border-[var(--color-accent)] text-[var(--color-accent)]'
                : 'border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text-main)]'"
              @click="activeTab = 'account'"
            >
              <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8">
                <circle cx="12" cy="8" r="3.5" />
                <path d="M4.5 20a7.5 7.5 0 0 1 15 0" />
              </svg>
              <span>Account</span>
            </button>
          </div>

          <button
            type="button"
            class="mb-2 rounded-md p-1 text-[var(--color-text-muted)] hover:bg-[var(--color-base-soft)] hover:text-[var(--color-text-main)]"
            aria-label="Close settings"
            @click="closeModal"
          >
            <svg viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="1.8">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </div>

        <div class="relative p-5">
          <LLMSettingsTab v-show="activeTab === 'llm'" @close-request="closeModal" />
          <WorkspaceTab
            v-show="activeTab === 'workspace'"
            :initial-step="initialStep"
            :modal-open="modelValue"
            @close-request="closeModal"
          />
          <AccountTab v-show="activeTab === 'account'" />
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { ref, watch } from 'vue'
import LLMSettingsTab from './tabs/LLMSettingsTab.vue'
import WorkspaceTab from './tabs/WorkspaceTab.vue'
import AccountTab from './tabs/AccountTab.vue'
import { useLLMConfig } from '../../composables/useLLMConfig'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  initialTab: {
    type: String,
    default: 'llm',
  },
  initialStep: {
    type: Number,
    default: 1,
  },
})

const emit = defineEmits(['update:modelValue'])
const llmConfig = useLLMConfig()

const activeTab = ref('llm')

function normalizeTab(tab) {
  const candidate = String(tab || '').toLowerCase()
  if (candidate === 'api') return 'llm'
  if (candidate === 'data') return 'workspace'
  if (candidate === 'llm' || candidate === 'workspace' || candidate === 'account') return candidate
  return 'llm'
}

watch(
  () => props.modelValue,
  (isOpen) => {
    if (isOpen) {
      activeTab.value = normalizeTab(props.initialTab)
    } else {
      llmConfig.clearSensitiveState()
    }
  },
  { immediate: true },
)

watch(
  () => props.initialTab,
  (tab) => {
    if (props.modelValue) {
      activeTab.value = normalizeTab(tab)
    }
  },
)

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
