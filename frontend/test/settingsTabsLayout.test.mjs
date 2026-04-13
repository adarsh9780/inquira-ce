import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('settings modal includes LLM, Workspace, and Account tabs with state-preserving v-show', () => {
  const path = resolve(process.cwd(), 'src/components/modals/SettingsModal.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('LLM &amp; API Keys'), true)
  assert.equal(source.includes('Workspace'), true)
  assert.equal(source.includes('Account'), true)
  assert.equal(source.includes('<LLMSettingsTab v-show="activeTab === \'llm\'" @close-request="closeModal" />'), true)
  assert.equal(source.includes('<WorkspaceTab'), true)
  assert.equal(source.includes("v-show=\"activeTab === 'workspace'\""), true)
  assert.equal(source.includes('<AccountTab v-show="activeTab === \'account\'" />'), true)
  assert.equal(source.includes("if (candidate === 'api') return 'llm'"), true)
})

test('packages tab routes installs to terminal workflow', () => {
  const path = resolve(process.cwd(), 'src/components/modals/PackagesTab.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('Install packages from Terminal'), true)
  assert.equal(source.includes('uv pip install package==version'), true)
  assert.equal(source.includes('appStore.toggleTerminal()'), true)
})
