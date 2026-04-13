<template>
  <section class="relative">
    <h2 class="mb-4 text-lg font-bold text-[var(--color-text-main)]">Workspace</h2>

    <WorkspaceStepper
      :current-step="currentStep"
      :ws-name="wsName"
      :file-selected="fileSelected"
      :saving-step="savingStep"
      @update:current-step="(value) => (currentStep = value)"
      @update:ws-name="(value) => (wsName = value)"
      @update:file-selected="(value) => (fileSelected = value)"
      @trigger-save="runSave"
    />

    <Transition
      enter-active-class="transition duration-200"
      enter-from-class="opacity-0 translate-y-2"
      leave-active-class="transition duration-150"
      leave-to-class="opacity-0 translate-y-2"
    >
      <div
        v-if="showToast"
        class="absolute -bottom-14 left-1/2 flex -translate-x-1/2 items-center gap-2 rounded-full bg-[#1C1A18] px-5 py-2.5 text-sm text-white"
      >
        <span class="text-[var(--color-success)]">✓</span>
        <span>Workspace 'IPL 2024' created successfully</span>
      </div>
    </Transition>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import WorkspaceStepper from '../WorkspaceStepper.vue'

const currentStep = ref(1)
const wsName = ref('')
const fileSelected = ref(false)
const savingStep = ref(0)
const showToast = ref(false)

async function runSave() {
  if (savingStep.value > 0) return

  currentStep.value = 4
  for (let i = 1; i <= 4; i += 1) {
    savingStep.value = i
    await new Promise((resolve) => setTimeout(resolve, i === 3 ? 900 : 600))
  }

  showToast.value = true
  setTimeout(() => {
    showToast.value = false
  }, 2800)
}
</script>
