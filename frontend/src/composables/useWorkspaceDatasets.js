export function useWorkspaceDatasets() {
  function normalizeDatasetName(value) {
    return String(value || '').trim()
  }

  return {
    normalizeDatasetName,
  }
}
