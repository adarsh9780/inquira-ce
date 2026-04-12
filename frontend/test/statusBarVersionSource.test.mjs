import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('status bar version label is sourced from frontend package version define', () => {
  const statusBarSource = readFileSync(resolve(process.cwd(), 'src/components/layout/StatusBar.vue'), 'utf-8')
  const viteConfigSource = readFileSync(resolve(process.cwd(), 'vite.config.js'), 'utf-8')

  assert.equal(viteConfigSource.includes('const frontendPackage = JSON.parse('), true)
  assert.equal(viteConfigSource.includes("const frontendRoot = fileURLToPath(new URL('.', import.meta.url))"), true)
  assert.equal(viteConfigSource.includes("readFileSync(resolve(frontendRoot, 'package.json'), 'utf-8')"), true)
  assert.equal(viteConfigSource.includes('__APP_VERSION__'), true)
  assert.equal(viteConfigSource.includes('JSON.stringify(frontendVersion)'), true)

  assert.equal(statusBarSource.includes('const uiVersion = String('), true)
  assert.equal(statusBarSource.includes("typeof __APP_VERSION__ !== 'undefined'"), true)
  assert.equal(statusBarSource.includes('Inquira v{{ uiVersion }}'), true)
})
