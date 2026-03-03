import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('TableTab uses workspace artifact catalog as canonical source and refreshes after runtime dataframe updates', () => {
  const path = resolve(process.cwd(), 'src/components/analysis/TableTab.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('const allArtifacts = computed(() => (Array.isArray(workspaceArtifacts.value) ? workspaceArtifacts.value : []))'), true)
  assert.equal(source.includes('appStore.dataframes.map((df) => String(df?.data?.artifact_id || \'\')).filter(Boolean).join(\'|\')'), true)
  assert.equal(source.includes('void loadWorkspaceArtifacts(appStore.activeWorkspaceId)'), true)
  assert.equal(source.includes('if (selectedArtifactId.value && !list.some((item) => item.artifact_id === selectedArtifactId.value))'), true)
})
