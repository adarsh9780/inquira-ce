import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, existsSync } from 'node:fs'
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

test('CE edition keeps local-only auth without restoring external auth modules', () => {
  const authServicePath = resolve(process.cwd(), '../backend/app/v1/services/auth_service.py')
  const externalAuthServicePath = resolve(process.cwd(), '../backend/app/v1/services/' + ['supa', 'base_auth_service.py'].join(''))
  const localAuthServicePath = resolve(process.cwd(), '../backend/app/v1/services/local_auth_service.py')
  assert.equal(existsSync(authServicePath), false, 'legacy auth_service.py should not exist in CE')
  assert.equal(existsSync(externalAuthServicePath), false, 'external auth service should not exist in CE')
  assert.equal(existsSync(localAuthServicePath), true, 'local auth service should exist in CE')

  const localStatePath = resolve(process.cwd(), 'src/services/localStateService.js')
  const localStateSource = readFileSync(localStatePath, 'utf-8')
  assert.equal(localStateSource.includes("const DEFAULT_SCOPE = 'anonymous'"), false)
  assert.equal(localStateSource.includes("const DEFAULT_SCOPE = 'default'"), true)
})
