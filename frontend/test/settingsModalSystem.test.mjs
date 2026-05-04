import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function read(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('settings modal uses v-model contract and two-column panel navigation', () => {
  const source = read('src/components/modals/SettingsModal.vue')

  assert.equal(source.includes('modelValue'), true)
  assert.equal(source.includes("defineEmits(['update:modelValue'])"), true)
  assert.equal(source.includes('const navLevel = ref(1)'), false)
  assert.equal(source.includes("const activeSection = ref('llm')"), true)
  assert.equal(source.includes("const currentPanel = ref('llm')"), true)
  assert.equal(source.includes("const panelDirection = ref('forward')"), true)
  assert.equal(source.includes('w-[190px]'), true)
  assert.equal(source.includes('max-w-[900px]'), true)
  assert.equal(source.includes('max-w-[980px]'), false)
  assert.equal(source.includes('openWorkspaceSection'), true)
  assert.equal(source.includes('closeWorkspaceLevel'), false)
  assert.equal(source.includes('@click="openWorkspaceSection"'), true)
  assert.equal(source.includes('Appearance'), true)
  assert.equal(source.includes('Terms &amp; Conditions'), true)
  assert.equal(source.includes("@click=\"openLeafSection('appearance')\""), true)
  assert.equal(source.includes("@click=\"openLeafSection('terms')\""), true)
  assert.equal(source.includes('<AppearanceTab />'), true)
  assert.equal(source.includes("<TermsTab :active=\"currentPanel === 'terms'\" />"), true)
  assert.equal(source.includes("if (candidate === 'legal') return 'terms'"), true)
  assert.equal(source.includes("if (candidate === 'llm' || candidate === 'workspace' || candidate === 'appearance' || candidate === 'account' || candidate === 'terms')"), true)
  assert.equal(source.includes('<span class="text-xs">›</span>'), false)
  assert.equal(source.includes('navigateTo'), true)
  assert.equal(source.includes("<LLMSettingsTab @close-request=\"closeModal\" />"), true)
  assert.equal(source.includes('scrollbar-hidden absolute inset-0 overflow-y-auto'), true)
  assert.equal(source.includes('<WorkspaceTab'), true)
  assert.equal(source.includes('panel-mode="ws-list"'), true)
  assert.equal(source.includes('panel-mode="ws-detail"'), true)
  assert.equal(source.includes('panel-mode="ws-create"'), true)
  assert.equal(source.includes('panelClass(\'ws-list\')'), true)
  assert.equal(source.includes("panelClass('terms')"), true)
  assert.equal(source.includes('panelClass(\'account\')'), true)
  assert.equal(source.includes("if (candidate === 'data') return 'workspace'"), true)
  assert.equal(source.includes("if (candidate === 'api') return 'llm'"), true)
  assert.equal(source.includes('activeTab ==='), false)
  assert.equal(source.includes("@import url('https://fonts.googleapis.com/css2?family=Ubuntu"), false)
})

test('workspace tab now uses list/detail/create panels instead of stepper flow', () => {
  const tabSource = read('src/components/modals/tabs/WorkspaceTab.vue')

  assert.equal(tabSource.includes("panelMode === 'ws-list'"), true)
  assert.equal(tabSource.includes("panelMode === 'ws-detail'"), true)
  assert.equal(tabSource.includes('New workspace'), true)
  assert.equal(tabSource.includes("@click=\"emit('navigate', 'ws-create', 'forward')\""), true)
  assert.equal(tabSource.includes("@click=\"emit('navigate', 'ws-list', 'backward')\""), true)
  assert.equal(tabSource.includes('max-w-[660px]'), false)
  assert.equal(tabSource.includes('title="Back to workspace list"'), true)
  assert.equal(tabSource.includes('aria-label="Back to workspace list"'), true)
  assert.equal(tabSource.includes('No workspaces yet'), true)
  assert.equal(tabSource.includes('Create your first workspace'), true)
  assert.equal(tabSource.includes('Delete workspace'), true)
  assert.equal(tabSource.includes('+ Add dataset'), true)
  assert.equal(tabSource.includes('title="Delete Dataset"'), true)
  assert.equal(tabSource.includes('Continue'), true)
  assert.equal(tabSource.includes('workspace-stepper'), true)
  assert.equal(tabSource.includes('workspace-stepper-line'), true)
  assert.equal(tabSource.includes('workspace-stepper-dot'), true)
  assert.equal(tabSource.includes('rounded-xl border border-[var(--color-border)] bg-[var(--color-base)]'), false)
  assert.equal(tabSource.includes('const currentStep = ref(1)'), false)
  assert.equal(tabSource.includes('const savingStep = ref(0)'), false)
  assert.equal(tabSource.includes("setInlineToast('Dataset added')"), false)
})

test('settings tab nested scroll containers hide scrollbars while keeping overflow active', () => {
  const tabPaths = [
    'src/components/modals/tabs/AccountTab.vue',
    'src/components/modals/tabs/AppearanceTab.vue',
    'src/components/modals/tabs/LLMSettingsTab.vue',
    'src/components/modals/tabs/TermsTab.vue',
    'src/components/modals/tabs/WorkspaceTab.vue',
  ]

  for (const path of tabPaths) {
    const source = read(path)
    assert.equal(source.includes('scrollbar-hidden'), true, `${path} should hide native scrollbars`)
    assert.equal(source.includes('overflow-y-auto'), true, `${path} should keep scroll behavior active`)
  }

  const llmSource = read('src/components/modals/tabs/LLMSettingsTab.vue')
  assert.equal(llmSource.includes('class="scrollbar-hidden h-full overflow-y-auto pb-24"'), true)
  assert.equal(llmSource.includes(":class=\"showAdvanced ? 'scrollbar-hidden' : ''\""), false)
})
