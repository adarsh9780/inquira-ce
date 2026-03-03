import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('table tab auto-selects latest dataframe artifact after new run', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/TableTab.vue'),
    'utf-8',
  )

  assert.equal(source.includes("const latestArtifactId = String(appStore.dataframes?.[0]?.data?.artifact_id || '').trim()"), true)
  assert.equal(source.includes('selectedArtifactId.value = latestArtifactId'), true)
})
