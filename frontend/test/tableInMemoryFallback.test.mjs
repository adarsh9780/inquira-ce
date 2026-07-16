import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('table tab does not use in-memory dataframe fallback for saved turn artifacts', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/TableTab.vue'),
    'utf-8',
  )

  assert.equal(source.includes("const MEMORY_ARTIFACT_PREFIX = 'memory:'"), false)
  assert.equal(source.includes('const memoryArtifacts = computed(() => {'), false)
  assert.equal(source.includes('if (isMemoryArtifactId(newId)) {'), false)
  assert.equal(source.includes('loadInMemoryArtifact(memoryArtifact)'), false)
  assert.equal(source.includes('label: isMemory ? `${label} (memory)` : label'), false)
  assert.equal(source.includes('apiService.getTurnDataframeArtifactRows('), true)
})
