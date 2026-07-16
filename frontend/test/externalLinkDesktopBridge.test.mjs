import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'

test('external link service routes desktop links through open_external_url command', () => {
  const path = resolve(process.cwd(), 'src/services/externalLinkService.js')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes("invoke('open_external_url', { url })"), true)
  assert.equal(source.includes('window.open(url, \"_blank\"') || source.includes("window.open(url, '_blank'"), true)
})

test('LLM settings use external link handler for provider URLs', () => {
  const path = resolve(process.cwd(), 'src/components/modals/tabs/LLMSettingsTab.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('@click.prevent="openProviderApiKeyPortal"'), true)
  assert.equal(source.includes('void openExternalUrl(url)'), true)
  assert.equal(source.includes("import { openExternalUrl } from '../../../services/externalLinkService'"), true)
})

test('StatusBar uses external link helper (CE: AuthModal removed)', () => {
  const statusBarPath = resolve(process.cwd(), 'src/components/layout/StatusBar.vue')
  const statusBarSource = readFileSync(statusBarPath, 'utf-8')
  assert.equal(statusBarSource.includes('@click.prevent="openInquiraSite"'), true)
  assert.equal(statusBarSource.includes("openExternalUrl('https://inquiraai.com')"), true)
  assert.equal(statusBarSource.includes('Inquira v{{ uiVersion }}'), true)
  assert.equal(statusBarSource.includes('typeof __APP_VERSION__ !== \'undefined\''), true)

  // CE: AuthModal.vue was deleted
  const authPath = resolve(process.cwd(), 'src/components/modals/AuthModal.vue')
  assert.equal(existsSync(authPath), false, 'AuthModal.vue should not exist in CE')
})

test('desktop runtime exposes open_external_url command handler', () => {
  const path = resolve(process.cwd(), '../src-tauri/src/lib.rs')
  const source = readFileSync(path, 'utf-8')
  const removedLoopbackCommand = ['auth_start', '_loopback_listener'].join('')
  const removedCallbackEvent = ['auth', ':callback'].join('')
  const removedFormParser = ['url::form', '_urlencoded::parse'].join('')

  assert.equal(source.includes('fn open_external_url(url: String) -> Result<(), String>'), true)
  assert.equal(source.includes('open_external_url,'), true)
  assert.equal(source.includes(`fn ${removedLoopbackCommand}`), false)
  assert.equal(source.includes(`"${removedCallbackEvent}"`), false)
  assert.equal(source.includes('error_description'), false)
  assert.equal(source.includes(removedFormParser), false)
  assert.equal(source.includes(`${removedLoopbackCommand},`), false)
})
