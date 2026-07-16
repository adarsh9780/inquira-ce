import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app shows one-shot toast feedback when workspace runtime bootstrap errors occur', () => {
  const appPath = resolve(process.cwd(), 'src/App.vue')
  const source = readFileSync(appPath, 'utf-8')

  assert.equal(source.includes("import { toast } from './composables/useToast'"), true)
  assert.equal(source.includes('() => appStore.runtimeError'), true)
  assert.equal(source.includes('if (!authStore.isAuthenticated) return'), true)
  assert.equal(source.includes("toast.error('Workspace Runtime Error', normalized)"), true)
  assert.equal(source.includes('if (normalized === lastRuntimeErrorToast.value) return'), true)
})
