import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function readSource(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('supabase auth service uses desktop PKCE flow for Google OAuth code exchange', () => {
  const source = readSource('src/services/supabaseAuthService.js')

  assert.equal(source.includes('window.__TAURI_INTERNALS__'), true)
  assert.equal(source.includes("flowType: isTauriDesktop() ? 'pkce' : 'implicit'"), true)
  assert.equal(source.includes('detectSessionInUrl: false'), true)
})
