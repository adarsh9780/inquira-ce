import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
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

test('StatusBar and AuthModal links use external link helper', () => {
  const statusBarPath = resolve(process.cwd(), 'src/components/layout/StatusBar.vue')
  const statusBarSource = readFileSync(statusBarPath, 'utf-8')
  assert.equal(statusBarSource.includes('@click.prevent="openGitHubRepo"'), true)
  assert.equal(statusBarSource.includes("openExternalUrl('https://github.com/adarsh9780/inquira')"), true)

  const authPath = resolve(process.cwd(), 'src/components/modals/AuthModal.vue')
  const authSource = readFileSync(authPath, 'utf-8')
  assert.equal(authSource.includes('@click.prevent="openTermsAndConditions"'), true)
  assert.equal(authSource.includes('import { openExternalUrl } from \'../../services/externalLinkService\''), true)
})

test('desktop runtime exposes open_external_url command handler', () => {
  const path = resolve(process.cwd(), '../src-tauri/src/lib.rs')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('fn open_external_url(url: String) -> Result<(), String>'), true)
  assert.equal(source.includes('open_external_url,'), true)
  assert.equal(source.includes('fn auth_start_loopback_listener(app: tauri::AppHandle) -> Result<AuthLoopbackResponse, String>'), true)
  assert.equal(source.includes('app_handle.emit("auth:callback"'), true)
  assert.equal(source.includes('auth_start_loopback_listener,'), true)
})
