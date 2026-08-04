import { describe, expect, it } from 'vitest'

import {
  artifactUnavailableDescription,
  isArtifactAvailable,
  isArtifactPayloadMissingError,
} from '../src/utils/artifactAvailability'

describe('artifact availability', () => {
  it('keeps only active or legacy status-less artifacts selectable', () => {
    expect(isArtifactAvailable({ status: 'active' })).toBe(true)
    expect(isArtifactAvailable({})).toBe(true)
    expect(isArtifactAvailable({ status: 'missing' })).toBe(false)
    expect(isArtifactAvailable(null)).toBe(false)
  })

  it('recognizes native missing-payload failures without relying on HTTP status', () => {
    expect(isArtifactPayloadMissingError(new Error(
      'artifact_payload_missing: Artifact payload is missing from local storage.',
    ))).toBe(true)
    expect(isArtifactPayloadMissingError({ status: 404 })).toBe(true)
    expect(isArtifactPayloadMissingError(new Error('database busy'))).toBe(false)
  })

  it('uses concise recovery copy instead of internal storage codes', () => {
    expect(artifactUnavailableDescription('table', 1)).toBe(
      'This saved table no longer has its local result file. Run the question again to recreate it.',
    )
    expect(artifactUnavailableDescription('chart', 2)).toBe(
      'These 2 saved charts no longer have their local result files. Run the question again to recreate them.',
    )
  })
})
