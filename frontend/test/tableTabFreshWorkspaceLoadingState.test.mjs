import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('TableTab shows saved-table loading only while an active turn artifact list is loading', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/TableTab.vue'),
    'utf-8',
  )

  assert.equal(source.includes('const workspaceKnownSavedTables = ref({})'), false)
  assert.equal(source.includes('const activeWorkspaceHasKnownSavedTables = computed(() => {'), false)
  assert.equal(source.includes('const showArtifactListLoadingState = computed(() => {'), true)
  assert.equal(source.includes('v-else-if="showArtifactListLoadingState"'), true)
  assert.equal(source.includes("return isLoadingArtifacts.value && Boolean(String(appStore.activeTurnId || '').trim())"), true)
  assert.equal(source.includes('[normalizedWorkspaceId]: artifacts.length > 0'), false)
})
