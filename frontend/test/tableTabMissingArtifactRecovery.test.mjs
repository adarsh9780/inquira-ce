import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('table tab removes missing payloads from selection and shows one recoverable state', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/TableTab.vue'),
    'utf-8',
  )

  assert.equal(source.includes('return isArtifactPayloadMissingError(error)'), true)
  assert.equal(source.includes("? { ...artifact, status: 'missing' }"), true)
  assert.equal(source.includes('title="Saved tables unavailable"'), true)
  assert.equal(source.includes("artifactUnavailableDescription('table', unavailableArtifactCount)"), true)
  assert.equal(source.includes("if (tableError.value) return tableError.value"), false)
  assert.equal(source.includes('artifact_payload_missing: Artifact payload is missing from local storage.'), false)
})
