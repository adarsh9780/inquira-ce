import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('auth boundary resets app state and clears schema/settings cache before user-scoped hydration', () => {
  const appPath = resolve(process.cwd(), 'src/App.vue')
  const source = readFileSync(appPath, 'utf-8')

  assert.equal(source.includes("import { previewService } from './services/previewService'"), true)
  assert.equal(source.includes('appStore.resetForAuthBoundary()'), true)
  assert.equal(source.includes('previewService.clearSchemaCache()'), true)
  assert.equal(source.includes('await appStore.loadLocalConfig(userId)'), true)
  assert.equal(source.includes('await appStore.loadLocalConfig()'), false)
})
