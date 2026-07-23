import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'

test('LLM settings use external link handler for provider URLs', () => {
  const path = resolve(process.cwd(), 'src/components/modals/tabs/LLMSettingsTab.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('@click.prevent="openProviderApiKeyPortal"'), true)
  assert.equal(source.includes('void openExternalUrl(url)'), true)
  assert.equal(source.includes("import { openExternalUrl } from '../../../services/externalLinkService'"), true)
})

test('StatusBar stays operational and does not duplicate product links or version copy', () => {
  const statusBarPath = resolve(process.cwd(), 'src/components/layout/StatusBar.vue')
  const statusBarSource = readFileSync(statusBarPath, 'utf-8')
  assert.equal(statusBarSource.includes('@click.prevent="openInquiraSite"'), false)
  assert.equal(statusBarSource.includes("openExternalUrl('https://inquiraai.com')"), false)
  assert.equal(statusBarSource.includes('Inquira v{{ uiVersion }}'), false)
  assert.equal(statusBarSource.includes('typeof __APP_VERSION__ !== \'undefined\''), false)
  assert.equal(statusBarSource.includes('data-background-operation-status'), true)

  // CE: AuthModal.vue was deleted
  const authPath = resolve(process.cwd(), 'src/components/modals/AuthModal.vue')
  assert.equal(existsSync(authPath), false, 'AuthModal.vue should not exist in CE')
})
