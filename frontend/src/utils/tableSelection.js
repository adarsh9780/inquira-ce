export function chooseTableSelectionAfterRefresh({
  currentSelectionId,
  availableArtifactIds,
  rememberedArtifactId,
  latestArtifactId,
  latestMemoryArtifactId,
  pendingAutoSelectArtifactId,
}) {
  const available = availableArtifactIds instanceof Set ? availableArtifactIds : new Set()

  const pending = String(pendingAutoSelectArtifactId || '').trim()
  if (pending && available.has(pending)) return pending

  const current = String(currentSelectionId || '').trim()
  if (current && available.has(current)) return current

  const remembered = String(rememberedArtifactId || '').trim()
  if (remembered && available.has(remembered)) return remembered

  const latest = String(latestArtifactId || '').trim()
  if (latest && available.has(latest)) return latest

  const latestMemory = String(latestMemoryArtifactId || '').trim()
  if (latestMemory && available.has(latestMemory)) return latestMemory

  return ''
}
