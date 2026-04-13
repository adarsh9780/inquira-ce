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
  assert.equal(source.includes("<WorkspaceTab v-show=\"activeTab === 'workspace'\" />"), true)
  assert.equal(source.includes("<AccountTab v-show=\"activeTab === 'account'\" />"), true)
  assert.equal(source.includes("@import url('https://fonts.googleapis.com/css2?family=Ubuntu"), true)
})

test('workspace tab and stepper include save flow, emitted contracts, and toast', () => {
  const tabSource = read('src/components/modals/tabs/WorkspaceTab.vue')
  const stepperSource = read('src/components/modals/WorkspaceStepper.vue')

  assert.equal(tabSource.includes('const currentStep = ref(1)'), true)
  assert.equal(tabSource.includes('const savingStep = ref(0)'), true)
  assert.equal(tabSource.includes('for (let i = 1; i <= 4; i += 1)'), true)
  assert.equal(tabSource.includes("Workspace 'IPL 2024' created successfully"), true)

  assert.equal(stepperSource.includes("defineEmits(['update:currentStep', 'update:wsName', 'update:fileSelected', 'triggerSave'])"), true)
  assert.equal(stepperSource.includes("@click=\"emit('triggerSave')\""), true)
  assert.equal(stepperSource.includes('animate-spin rounded-full border-2 border-[var(--color-accent)] border-t-transparent'), true)
})
