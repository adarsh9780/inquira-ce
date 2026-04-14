import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('settings modal includes sliding left-nav levels and panel routing', () => {
  const path = resolve(process.cwd(), 'src/components/modals/SettingsModal.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('LLM &amp; API Keys'), true)
  assert.equal(source.includes('Workspace'), true)
  assert.equal(source.includes('Account'), true)
  assert.equal(source.includes('Workspaces'), true)
  assert.equal(source.includes('Back'), true)
  assert.equal(source.includes(':style="{ transform: navLevel === 1 ? \'translateX(0%)\' : \'translateX(-100%)\', transitionTimingFunction: \'cubic-bezier(0.4,0,0.2,1)\' }"'), true)
  assert.equal(source.includes(':style="{ transform: navLevel === 2 ? \'translateX(0%)\' : \'translateX(100%)\', transitionTimingFunction: \'cubic-bezier(0.4,0,0.2,1)\' }"'), true)
  assert.equal(source.includes('<LLMSettingsTab @close-request="closeModal" />'), true)
  assert.equal(source.includes('<WorkspaceTab'), true)
  assert.equal(source.includes("panel-mode=\"ws-list\""), true)
  assert.equal(source.includes("panel-mode=\"ws-detail\""), true)
  assert.equal(source.includes("panel-mode=\"ws-create\""), true)
  assert.equal(source.includes('<AccountTab />'), true)
  assert.equal(source.includes('activeTab ==='), false)
  assert.equal(source.includes("if (candidate === 'api') return 'llm'"), true)
})

test('packages tab routes installs to terminal workflow', () => {
  const path = resolve(process.cwd(), 'src/components/modals/PackagesTab.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('Install packages from Terminal'), true)
  assert.equal(source.includes('uv pip install package==version'), true)
  assert.equal(source.includes('appStore.toggleTerminal()'), true)
})
