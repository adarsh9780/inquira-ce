import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('vite exposes root supabase env variables to the desktop frontend', () => {
  const source = readFileSync(resolve(process.cwd(), 'vite.config.js'), 'utf-8')

  assert.equal(source.includes("envDir: '..'"), true)
  assert.equal(source.includes("envPrefix: ['VITE_', 'SB_INQUIRA_CE_']"), true)
})

test('supabase auth service accepts SB-prefixed env names directly', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/services/supabaseAuthService.js'),
    'utf-8',
  )

  assert.equal(source.includes("readEnv('VITE_SB_INQUIRA_CE_URL', 'SB_INQUIRA_CE_URL')"), true)
  assert.equal(source.includes("'SB_INQUIRA_CE_PUBLISHABLE_KEY'"), true)
  assert.equal(source.includes('root .env file'), true)
  assert.equal(source.includes('exchangeCodeForSession(code)'), true)
  assert.equal(source.includes('Supabase auth callback returned an error'), true)
})
