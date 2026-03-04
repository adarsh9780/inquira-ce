import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('table tab supports in-memory dataframe fallback when scratchpad artifacts are missing', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/TableTab.vue'),
    'utf-8',
  )

  assert.equal(source.includes("const MEMORY_ARTIFACT_PREFIX = 'memory:'"), true)
  assert.equal(source.includes('const memoryArtifacts = computed(() => {'), true)
  assert.equal(source.includes('if (isMemoryArtifactId(newId)) {'), true)
  assert.equal(source.includes('loadInMemoryArtifact(memoryArtifact)'), true)
  assert.equal(source.includes('label: isMemory ? `${label} (memory)` : label'), true)
})
