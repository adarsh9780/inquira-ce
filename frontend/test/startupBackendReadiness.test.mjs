import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('authenticated workspace shell mounts only after account bootstrap completes', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/App.vue'), 'utf-8')

  assert.equal(
    /<AppShell\s+v-if="authStore\.isAuthenticated && appBootstrap\.ready && !modelOnboarding\.required"/.test(source),
    true,
    'main workspace shell must not mount hidden child components before backend and workspace bootstrap finish',
  )
  assert.equal(
    source.includes('<div v-show="authStore.isAuthenticated && appBootstrap.ready" class="flex flex-col h-screen">'),
    false,
    'v-show keeps chat/workspace components mounted and can fire workspace API calls before startup readiness',
  )
})
