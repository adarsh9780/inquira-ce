import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('CE package does not depend on Supabase auth', () => {
  const packageJson = JSON.parse(readFileSync(resolve(process.cwd(), 'package.json'), 'utf-8'))
  const dependencies = packageJson.dependencies || {}
  const externalAuthPackage = ['@supa', 'base/supa', 'base-js'].join('')

  assert.equal(Object.hasOwn(dependencies, externalAuthPackage), false)
})

test('CE Vite config does not expose Supabase auth env prefixes', () => {
  const source = readFileSync(resolve(process.cwd(), 'vite.config.js'), 'utf-8')
  const externalAuthEnvPrefix = ['SB', '_INQUIRA', '_CE_'].join('')

  assert.equal(source.includes(externalAuthEnvPrefix), false)
})
