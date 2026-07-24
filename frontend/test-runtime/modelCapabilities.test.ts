import { describe, expect, it } from 'vitest'

import {
  modelSupportsImages,
  SUPPORTED_CHAT_IMAGE_TYPES,
} from '../src/utils/modelCapabilities'

describe('model image capabilities', () => {
  it('recognizes known multimodal model families', () => {
    expect(modelSupportsImages('openai/gpt-4.1-mini')).toBe(true)
    expect(modelSupportsImages('anthropic/claude-sonnet-4')).toBe(true)
    expect(modelSupportsImages('text-only-model')).toBe(false)
  })

  it('accepts only the supported chat image media types', () => {
    expect(SUPPORTED_CHAT_IMAGE_TYPES.has('image/png')).toBe(true)
    expect(SUPPORTED_CHAT_IMAGE_TYPES.has('image/svg+xml')).toBe(false)
  })
})
