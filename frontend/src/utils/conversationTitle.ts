export const CONVERSATION_TITLE_MAX_CHARACTERS = 80

const DEFAULT_CONVERSATION_TITLE = 'New conversation'

export function deriveConversationTitle(question: unknown): string {
  const normalized = String(question || '').replace(/\s+/g, ' ').trim()
  if (!normalized) return DEFAULT_CONVERSATION_TITLE

  const characters = Array.from(normalized)
  if (characters.length <= CONVERSATION_TITLE_MAX_CHARACTERS) return normalized

  return `${characters
    .slice(0, CONVERSATION_TITLE_MAX_CHARACTERS - 1)
    .join('')
    .trimEnd()}…`
}
