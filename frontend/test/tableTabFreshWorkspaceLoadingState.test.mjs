import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('TableTab does not show saved-table loading spinner for fresh workspaces', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/TableTab.vue'),
    'utf-8',
  )

  assert.equal(source.includes('const workspaceKnownSavedTables = ref({})'), true)
  assert.equal(source.includes('const activeWorkspaceHasKnownSavedTables = computed(() => {'), true)
  assert.equal(source.includes('const showArtifactListLoadingState = computed(() => {'), true)
  assert.equal(source.includes('v-else-if="showArtifactListLoadingState"'), true)
  assert.equal(source.includes('[normalizedWorkspaceId]: artifacts.length > 0'), true)
})
