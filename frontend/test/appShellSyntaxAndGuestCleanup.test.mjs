import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { compileScript, parse } from '@vue/compiler-sfc'

test('App shell SFC script compiles cleanly for startup/auth orchestration', () => {
  const appPath = resolve(process.cwd(), 'src/App.vue')
  const source = readFileSync(appPath, 'utf-8')
  const parsed = parse(source, { filename: 'App.vue' })

  assert.doesNotThrow(() => {
    compileScript(parsed.descriptor, { id: 'app-shell-startup-test' })
  })

  assert.equal(
    source.includes('if (authStore.isAuthenticated && !appBootstrap.ready && !appBootstrap.active) {'),
    true,
    'App startup should explicitly bootstrap the shell even when guest mode keeps the same local-user id',
  )
  assert.equal(
    source.includes('await handleAuthenticated(authStore.user)'),
    true,
    'App startup should call the shared authenticated bootstrap after auth initialization completes',
  )
})

test('CE local state uses a stable default scope', () => {
  const localStatePath = resolve(process.cwd(), 'src/services/localStateService.ts')
  const localStateSource = readFileSync(localStatePath, 'utf-8')
  assert.equal(localStateSource.includes("const DEFAULT_SCOPE = 'anonymous'"), false)
  assert.equal(localStateSource.includes("const DEFAULT_SCOPE = 'default'"), true)
})
