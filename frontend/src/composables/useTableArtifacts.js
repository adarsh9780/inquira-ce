export function useTableArtifacts() {
  function normalizeArtifactId(value) {
    return String(value || '').trim()
  }

  return {
    normalizeArtifactId,
  }
}
