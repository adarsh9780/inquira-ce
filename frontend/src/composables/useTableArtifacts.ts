export function useTableArtifacts() {
  function normalizeArtifactId(value: unknown): string {
    return String(value || '').trim()
  }

  return {
    normalizeArtifactId,
  }
}
