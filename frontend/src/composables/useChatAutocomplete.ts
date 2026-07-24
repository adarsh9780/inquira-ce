export function useChatAutocomplete() {
  function normalizeAutocompleteQuery(value: unknown): string {
    return String(value || '').trim()
  }

  return {
    normalizeAutocompleteQuery,
  }
}
