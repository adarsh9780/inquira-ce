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
})

test('CE edition keeps guest-first auth without restoring the old auth_service module', () => {
  const authServicePath = resolve(process.cwd(), '../backend/app/v1/services/auth_service.py')
  const supabaseAuthServicePath = resolve(process.cwd(), '../backend/app/v1/services/supabase_auth_service.py')
  assert.equal(existsSync(authServicePath), false, 'legacy auth_service.py should not exist in CE')
  assert.equal(existsSync(supabaseAuthServicePath), true, 'guest-first Supabase auth service should exist in CE')

  const localStatePath = resolve(process.cwd(), 'src/services/localStateService.js')
  const localStateSource = readFileSync(localStatePath, 'utf-8')
  assert.equal(localStateSource.includes("const DEFAULT_SCOPE = 'anonymous'"), false)
  assert.equal(localStateSource.includes("const DEFAULT_SCOPE = 'default'"), true)
})
