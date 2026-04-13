import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function read(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('settings modal uses v-model contract and preserves tab state with v-show', () => {
  const source = read('src/components/modals/SettingsModal.vue')

  assert.equal(source.includes('modelValue'), true)
  assert.equal(source.includes("defineEmits(['update:modelValue'])"), true)
  assert.equal(source.includes("<LLMSettingsTab v-show=\"activeTab === 'llm'\" />"), true)
  assert.equal(source.includes('<WorkspaceTab'), true)
  assert.equal(source.includes(':initial-step="initialStep"'), true)
  assert.equal(source.includes(':modal-open="modelValue"'), true)
  assert.equal(source.includes('@close-request="closeModal"'), true)
  assert.equal(source.includes('initialStep: {'), true)
  assert.equal(source.includes("<AccountTab v-show=\"activeTab === 'account'\" />"), true)
  assert.equal(source.includes("@import url('https://fonts.googleapis.com/css2?family=Ubuntu"), true)
})

test('workspace tab and stepper include dataset-management and save flow behavior', () => {
  const tabSource = read('src/components/modals/tabs/WorkspaceTab.vue')
  const stepperSource = read('src/components/modals/WorkspaceStepper.vue')

  assert.equal(tabSource.includes('const currentStep = ref(1)'), true)
  assert.equal(tabSource.includes('const savingStep = ref(0)'), true)
  assert.equal(tabSource.includes('for (let i = 1; i <= 4; i += 1)'), true)
  assert.equal(tabSource.includes("Workspace '{{ wsName || 'Untitled' }}' created successfully"), true)
  assert.equal(tabSource.includes('const isDatasetManagementMode = computed(() => normalizedInitialStep.value === 2)'), true)
  assert.equal(tabSource.includes("setInlineToast('Dataset added')"), true)
  assert.equal(tabSource.includes("setInlineToast('Dataset removed')"), true)
  assert.equal(tabSource.includes("emit('close-request')"), true)

  assert.equal(stepperSource.includes("'toggle-compact-dropzone'"), true)
  assert.equal(stepperSource.includes("'refresh-dataset'"), true)
  assert.equal(stepperSource.includes("'request-remove-dataset'"), true)
  assert.equal(stepperSource.includes("'confirm-remove-dataset'"), true)
  assert.equal(stepperSource.includes("@click=\"emit('trigger-save')\""), true)
  assert.equal(stepperSource.includes('animate-spin rounded-full border-2 border-[var(--color-accent)] border-t-transparent'), true)
})
