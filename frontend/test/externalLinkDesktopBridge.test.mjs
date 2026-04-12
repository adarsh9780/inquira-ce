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

test('ApiTab uses external link handler for provider URLs', () => {
  const path = resolve(process.cwd(), 'src/components/modals/ApiTab.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('@click.prevent="openLink(openrouterAccountModelsUrl)"'), true)
  assert.equal(source.includes('@click.prevent="openLink(providerKeyUrl)"'), true)
  assert.equal(source.includes('import { openExternalUrl } from \'../../services/externalLinkService\''), true)
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

  assert.equal(source.includes('fn open_external_url(url: String) -> Result<(), String>'), true)
  assert.equal(source.includes('open_external_url,'), true)
  assert.equal(source.includes('fn auth_start_loopback_listener(app: tauri::AppHandle) -> Result<AuthLoopbackResponse, String>'), true)
  assert.equal(source.includes('app_handle.emit('), true)
  assert.equal(source.includes('"auth:callback"'), true)
  assert.equal(source.includes('error_description'), true)
  assert.equal(source.includes('url::form_urlencoded::parse'), true)
  assert.equal(source.includes('auth_start_loopback_listener,'), true)
})
