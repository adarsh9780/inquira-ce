import { describe, expect, it } from 'vitest'
import {
  CONVERSATION_TITLE_MAX_CHARACTERS,
  deriveConversationTitle,
} from '../src/utils/conversationTitle'

describe('deriveConversationTitle', () => {
  it('uses the normalized first question for a new conversation title', () => {
    expect(deriveConversationTitle('  Give me\n  the top 10 bowlers  ')).toBe('Give me the top 10 bowlers')
  })

  it('limits long titles without splitting Unicode characters', () => {
    const title = deriveConversationTitle(`🏏${'a'.repeat(100)}`)

    expect(Array.from(title)).toHaveLength(CONVERSATION_TITLE_MAX_CHARACTERS)
    expect(title.startsWith('🏏')).toBe(true)
    expect(title.endsWith('…')).toBe(true)
  })

  it('provides a stable fallback when no question text is available', () => {
    expect(deriveConversationTitle('   ')).toBe('New conversation')
  })

  it('creates a readable title for the attachment-only prompt', () => {
    expect(deriveConversationTitle('Please analyze the attached image(s).')).toBe(
      'Please analyze the attached image(s).',
    )
  })
})
