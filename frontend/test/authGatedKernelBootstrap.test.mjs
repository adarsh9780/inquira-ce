import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('workspace kernel bootstrap in app store is gated by authentication state', () => {
  const appStorePath = resolve(process.cwd(), 'src/stores/appStore.js')
  const source = readFileSync(appStorePath, 'utf-8')

  assert.equal(source.includes("import { useAuthStore } from './authStore'"), true)
  assert.equal(source.includes('const authStore = useAuthStore()'), true)
  assert.equal(source.includes('if (!authStore.isAuthenticated) return false'), true)
  assert.equal(source.includes('if (!workspaceId || !authStore.isAuthenticated) return'), true)
})
