import assert from 'node:assert/strict'
import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

test('TypeScript is incremental, strict for typed files, and checked independently', () => {
  const packageJson = JSON.parse(readFileSync(resolve(process.cwd(), 'package.json'), 'utf8'))
  const tsconfig = JSON.parse(readFileSync(resolve(process.cwd(), 'tsconfig.json'), 'utf8'))

  assert.equal(packageJson.scripts.typecheck, 'vue-tsc --noEmit')
  assert.equal(tsconfig.compilerOptions.strict, true)
  assert.equal(tsconfig.compilerOptions.allowJs, true)
  assert.equal(tsconfig.compilerOptions.checkJs, false)
  assert.equal(tsconfig.compilerOptions.noEmit, true)
})

test('shared domain types cover the current Wails application boundaries', () => {
  for (const file of [
    'api.ts',
    'artifact.ts',
    'conversation.ts',
    'execution.ts',
    'identifiers.ts',
    'preferences.ts',
    'workspace.ts',
  ]) {
    assert.equal(existsSync(resolve(process.cwd(), 'src/types', file)), true, `${file} is missing`)
  }
})

test('new domain stores must be TypeScript during the compatibility migration', () => {
  const stores = readdirSync(resolve(process.cwd(), 'src/stores'))
  const allowedLegacyStores = new Set(['appStore.js', 'authStore.js'])
  const unexpectedJavaScriptStores = stores.filter((file) => file.endsWith('.js') && !allowedLegacyStores.has(file))

  assert.deepEqual(unexpectedJavaScriptStores, [])
})
