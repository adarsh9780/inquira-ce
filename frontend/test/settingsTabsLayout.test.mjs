import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('settings modal includes a dedicated Packages tab', () => {
  const path = resolve(process.cwd(), 'src/components/modals/SettingsModal.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes("activeTab = 'packages'"), true)
  assert.equal(source.includes('<PackagesTab v-if="activeTab === \'packages\'" />'), true)
  assert.equal(source.includes("['api', 'data', 'packages', 'account']"), true)
})

test('packages tab routes installs to terminal workflow', () => {
  const path = resolve(process.cwd(), 'src/components/modals/PackagesTab.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('Install packages from Terminal'), true)
  assert.equal(source.includes('uv pip install package==version'), true)
  assert.equal(source.includes('appStore.toggleTerminal()'), true)
})
