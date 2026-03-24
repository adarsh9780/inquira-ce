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
})

test('repo does not keep guest or anonymous auth fallbacks after auth-shell redesign', () => {
  const authServicePath = resolve(process.cwd(), '../backend/app/v1/services/auth_service.py')
  const authServiceSource = readFileSync(authServicePath, 'utf-8')
  const localStatePath = resolve(process.cwd(), 'src/services/localStateService.js')
  const localStateSource = readFileSync(localStatePath, 'utf-8')

  assert.equal(authServiceSource.includes('ANONYMOUS_USER_ID'), false)
  assert.equal(authServiceSource.includes('def get_anonymous_user'), false)
  assert.equal(authServiceSource.includes('username="guest"'), false)
  assert.equal(localStateSource.includes("const DEFAULT_SCOPE = 'anonymous'"), false)
  assert.equal(localStateSource.includes("const DEFAULT_SCOPE = 'default'"), true)
})
