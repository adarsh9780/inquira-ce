import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('authenticated app bootstrap reuses auth hydration instead of re-fetching the profile', () => {
  const appSource = readFileSync(
    resolve(process.cwd(), 'src/App.vue'),
    'utf-8',
  )
  const authSource = readFileSync(
    resolve(process.cwd(), 'src/stores/authStore.js'),
    'utf-8',
  )

  assert.equal(appSource.includes('await authStore.refreshPlan()'), false)
  assert.equal(authSource.includes("plan.value = profile.plan || 'FREE'"), true)
})
