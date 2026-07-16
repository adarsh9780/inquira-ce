export function useChatAutocomplete() {
  function normalizeAutocompleteQuery(value) {
    return String(value || '').trim()
  }

  return {
    normalizeAutocompleteQuery,
  }
}
