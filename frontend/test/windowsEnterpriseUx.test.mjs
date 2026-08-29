import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const read = (path) => readFileSync(new URL(path, import.meta.url), 'utf8')

test('Windows installer asks for and records an approved data and runtime location', () => {
  const installer = read('../../build/windows/installer/project.nsi')
  assert.match(installer, /Page custom InquiraDataDirectoryPage InquiraDataDirectoryLeave/)
  assert.match(installer, /Choose data and runtime location/)
  assert.match(installer, /WriteRegStr HKCU "Software\\Inquira" "DataRoot"/)
})

test('settings expose global and per-provider enterprise network controls', () => {
  const settingsModal = read('../src/components/modals/SettingsModal.vue')
  const networkTab = read('../src/components/modals/tabs/NetworkSettingsTab.vue')
  const llmTab = read('../src/components/modals/tabs/LLMSettingsTab.vue')

  assert.match(settingsModal, /Network &amp; proxy/)
  assert.match(networkTab, /Use operating-system proxy/)
  assert.match(networkTab, /Use custom proxy/)
  assert.match(networkTab, /CA certificate bundle/)
  assert.match(networkTab, /without changing the operating-system trust store/)
  assert.match(llmTab, /Use global proxy settings/)
  assert.match(llmTab, /Provider network override/)
  assert.match(llmTab, /client private key/i)
})

test('OpenAI compatible provider includes endpoint auth model and certificate fields', () => {
  const llmTab = read('../src/components/modals/tabs/LLMSettingsTab.vue')
  const config = read('../src/composables/useLLMConfig.ts')

  assert.match(llmTab, /value: 'openai-compatible'/)
  assert.match(llmTab, /v-model="compatibleBaseUrl"/)
  assert.match(llmTab, /v-model="apiKeyHeader"/)
  assert.match(llmTab, /v-model="apiVersion"/)
  assert.match(llmTab, /v-model="providerClientCertificatePath"/)
  assert.match(config, /provider_settings: currentProviderSettings\(\)/)
})

test('desktop bundles selectable fonts and uses one focus border', () => {
  const packageJson = JSON.parse(read('../package.json'))
  const main = read('../src/main.ts')
  const styles = read('../src/style.css')

  assert.equal(typeof packageJson.dependencies['@fontsource/inter'], 'string')
  assert.equal(typeof packageJson.dependencies['@fontsource/jetbrains-mono'], 'string')
  assert.match(main, /import '\.\/fonts\.css'/)
  assert.match(styles, /:focus-visible\s*\{[^}]*outline:\s*1px solid/s)
  assert.match(styles, /--tw-ring-shadow:\s*0 0 #0000 !important/)
})

test('essential loading indicators continue under Windows reduced-motion policy', () => {
  const styles = read('../src/style.css')
  assert.match(styles, /@media \(prefers-reduced-motion: reduce\)[\s\S]*\.loading-spinner,[\s\S]*\.animate-spin[\s\S]*animation-iteration-count:\s*infinite !important/)
  assert.match(styles, /@keyframes inquira-spin/)
  assert.match(styles, /will-change:\s*transform/)
})
