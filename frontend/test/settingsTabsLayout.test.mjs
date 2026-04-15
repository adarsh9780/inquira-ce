import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('settings modal keeps left nav static and routes workspace panels on the right', () => {
  const path = resolve(process.cwd(), 'src/components/modals/SettingsModal.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('LLM &amp; API Keys'), true)
  assert.equal(source.includes('Workspace'), true)
  assert.equal(source.includes('Appearance'), true)
  assert.equal(source.includes('Account'), true)
  assert.equal(source.includes('const navLevel = ref(1)'), false)
  assert.equal(source.includes('openWorkspaceSection'), true)
  assert.equal(source.includes('closeWorkspaceLevel'), false)
  assert.equal(source.includes('<span class="text-xs">›</span>'), false)
  assert.equal(source.includes('<LLMSettingsTab @close-request="closeModal" />'), true)
  assert.equal(source.includes('<WorkspaceTab'), true)
  assert.equal(source.includes("panel-mode=\"ws-list\""), true)
  assert.equal(source.includes("panel-mode=\"ws-detail\""), true)
  assert.equal(source.includes("panel-mode=\"ws-create\""), true)
  assert.equal(source.includes('<AppearanceTab />'), true)
  assert.equal(source.includes('<AccountTab />'), true)
  assert.equal(source.includes('activeTab ==='), false)
  assert.equal(source.includes("if (candidate === 'api') return 'llm'"), true)
  assert.equal(source.includes("if (candidate === 'llm' || candidate === 'workspace' || candidate === 'appearance' || candidate === 'account')"), true)
})

test('packages tab routes installs to terminal workflow', () => {
  const path = resolve(process.cwd(), 'src/components/modals/PackagesTab.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('Install packages from Terminal'), true)
  assert.equal(source.includes('uv pip install package==version'), true)
  assert.equal(source.includes('appStore.toggleTerminal()'), true)
})
