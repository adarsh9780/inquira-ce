import { describe, expect, it } from 'vitest'

import {
  mergeModelOptions,
  normalizeModelOptions,
  optionMatchesSearch,
  prettifyModelName,
  providerLabel,
} from '../src/components/ui/modelDropdownUtils'

describe('model dropdown helpers', () => {
  it('normalizes primitive and object options and removes duplicates', () => {
    expect(normalizeModelOptions([
      'openai/gpt-4.1',
      { id: 'openai/gpt-4.1', name: 'Duplicate' },
      { value: 'anthropic/claude-sonnet-4', tags: ['Vision'] },
    ])).toEqual([
      {
        value: 'openai/gpt-4.1',
        label: 'GPT 4.1',
        provider: 'openai',
        tags: [],
      },
      {
        value: 'anthropic/claude-sonnet-4',
        label: 'Claude Sonnet 4',
        provider: 'anthropic',
        tags: ['vision'],
      },
    ])
  })

  it('merges options and searches labels, providers, and tags', () => {
    const options = mergeModelOptions(
      [{ value: 'openai/gpt-4.1', label: 'GPT 4.1' }],
      [{ value: 'google/gemini-flash', label: 'Gemini Flash', tags: ['fast'] }],
    )

    expect(options).toHaveLength(2)
    expect(optionMatchesSearch(options[1], 'fast')).toBe(true)
    expect(optionMatchesSearch(options[0], 'google')).toBe(false)
  })

  it('formats provider and model labels', () => {
    expect(providerLabel('openrouter')).toBe('OpenRouter')
    expect(prettifyModelName('openrouter/free')).toBe('OpenRouter Free')
  })
})
