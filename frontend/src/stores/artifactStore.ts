import { defineStore } from 'pinia'
import { ref } from 'vue'
import { normalizePlotlyFigure } from '../utils/figurePayload'

export const useArtifactStore = defineStore('artifacts', () => {
  let persistChange: (() => void) | null = null
  const activeTurnArtifactRefreshKey = ref(0)
  const resultData = ref<unknown>(null)
  const plotlyFigure = ref<unknown>(null)
  const dataframes = ref<Record<string, any>[]>([])
  const figures = ref<Record<string, any>[]>([])
  const scalars = ref<Record<string, any>[]>([])
  const promotedUserDataframes = ref<Record<string, any>[]>([])
  const promotedUserFigures = ref<Record<string, any>[]>([])
  const dataframeCount = ref(0)
  const tableRowCount = ref(0)
  const tableWindowStart = ref(0)
  const tableWindowEnd = ref(0)
  const tablePageOffsets = ref<Record<string, number>>({})
  const selectedTableArtifactsByWorkspace = ref<Record<string, string>>({})
  const selectedFigureArtifactsByWorkspace = ref<Record<string, string>>({})
  const dataPaneError = ref('')
  const figureCount = ref(0)

  function configurePersistence(handler: (() => void) | null) {
    persistChange = handler
  }

  function setResultData(data: unknown) {
    resultData.value = data
  }

  function setPlotlyFigure(figure: unknown) {
    plotlyFigure.value = figure
  }

  function setDataframes(items: unknown) {
    dataframes.value = Array.isArray(items) ? items as Record<string, any>[] : []
    dataframeCount.value = dataframes.value.length
  }

  function setFigures(items: unknown) {
    if (!Array.isArray(items)) {
      figures.value = []
      figureCount.value = 0
      return
    }
    figures.value = items
      .map((item, index) => {
        const figure = item as Record<string, unknown>
        const normalized = normalizePlotlyFigure(figure?.data ?? figure)
        if (!normalized) return null
        const normalizedRecord = normalized as Record<string, unknown>
        const artifactId = String(figure?.artifact_id || normalizedRecord?.artifact_id || '').trim()
        const logicalName = String(figure?.logical_name || normalizedRecord?.logical_name || figure?.name || '').trim()
        return {
          ...figure,
          name: String(figure?.name || `figure_${index + 1}`),
          artifact_id: artifactId || undefined,
          logical_name: logicalName || undefined,
          data: normalized,
        }
      })
      .filter((item): item is NonNullable<typeof item> => Boolean(item))
    figureCount.value = figures.value.length
  }

  function setScalars(items: unknown) {
    scalars.value = Array.isArray(items) ? items as Record<string, any>[] : []
  }

  function removeResultArtifact(artifactId: unknown) {
    const target = String(artifactId || '').trim()
    if (!target) return
    const artifactIdentity = (item: unknown) => {
      const record = (item || {}) as Record<string, unknown>
      const data = (record.data || {}) as Record<string, unknown>
      return String(data.artifact_id || record.artifact_id || '').trim()
    }
    dataframes.value = dataframes.value.filter((item) => artifactIdentity(item) !== target)
    figures.value = figures.value.filter((item) => artifactIdentity(item) !== target)
    scalars.value = scalars.value.filter((item) => artifactIdentity(item) !== target)
    dataframeCount.value = dataframes.value.length
    figureCount.value = figures.value.length
  }

  function setDataframeCount(count: unknown) {
    dataframeCount.value = Number(count || 0)
  }

  function setFigureCount(count: unknown) {
    figureCount.value = Number(count || 0)
  }

  function setDataPaneError(message: unknown) {
    dataPaneError.value = String(message || '')
  }

  function clearDataPaneError() {
    dataPaneError.value = ''
  }

  function setTableViewport(start: unknown, end: unknown, total: unknown) {
    const nextStart = Math.max(0, Number(start || 0))
    const nextEnd = Math.max(0, Number(end || 0))
    const nextTotal = Math.max(0, Number(total || 0))
    if (
      tableWindowStart.value === nextStart
      && tableWindowEnd.value === nextEnd
      && tableRowCount.value === nextTotal
    ) return
    tableWindowStart.value = nextStart
    tableWindowEnd.value = nextEnd
    tableRowCount.value = nextTotal
  }

  function clearTableViewport() {
    tableWindowStart.value = 0
    tableWindowEnd.value = 0
    tableRowCount.value = 0
  }

  function scopedKey(workspaceId: unknown, artifactId: unknown, turnId: unknown) {
    return `${String(workspaceId || '').trim()}::${String(turnId || '').trim() || 'workspace'}::${String(artifactId || '').trim()}`
  }

  function selectionKey(workspaceId: unknown, turnId: unknown) {
    const workspace = String(workspaceId || '').trim()
    return workspace ? `${workspace}::${String(turnId || '').trim() || 'workspace'}` : ''
  }

  function setTablePageOffset(workspaceId: unknown, artifactId: unknown, page: unknown, turnId: unknown = '') {
    const key = scopedKey(workspaceId, artifactId, turnId)
    const normalizedPage = Math.max(0, Number(page || 0))
    if (!key || key === '::workspace::' || Number(tablePageOffsets.value[key] || 0) === normalizedPage) return
    tablePageOffsets.value = { ...tablePageOffsets.value, [key]: normalizedPage }
    persistChange?.()
  }

  function getTablePageOffset(workspaceId: unknown, artifactId: unknown, turnId: unknown = '') {
    return Math.max(0, Number(tablePageOffsets.value[scopedKey(workspaceId, artifactId, turnId)] || 0))
  }

  function setSelectedArtifact(
    collection: typeof selectedTableArtifactsByWorkspace,
    workspaceId: unknown,
    artifactId: unknown,
    turnId: unknown,
  ) {
    const key = selectionKey(workspaceId, turnId)
    if (!key) return
    const artifact = String(artifactId || '').trim()
    const next = { ...collection.value }
    if (artifact) next[key] = artifact
    else delete next[key]
    collection.value = next
    persistChange?.()
  }

  function setSelectedTableArtifact(workspaceId: unknown, artifactId: unknown, turnId: unknown = '') {
    setSelectedArtifact(selectedTableArtifactsByWorkspace, workspaceId, artifactId, turnId)
  }

  function getSelectedTableArtifact(workspaceId: unknown, turnId: unknown = '') {
    return String(selectedTableArtifactsByWorkspace.value[selectionKey(workspaceId, turnId)] || '').trim()
  }

  function setSelectedFigureArtifact(workspaceId: unknown, artifactId: unknown, turnId: unknown = '') {
    setSelectedArtifact(selectedFigureArtifactsByWorkspace, workspaceId, artifactId, turnId)
  }

  function getSelectedFigureArtifact(workspaceId: unknown, turnId: unknown = '') {
    return String(selectedFigureArtifactsByWorkspace.value[selectionKey(workspaceId, turnId)] || '').trim()
  }

  function reset() {
    activeTurnArtifactRefreshKey.value = 0
    resultData.value = null
    plotlyFigure.value = null
    dataframes.value = []
    figures.value = []
    scalars.value = []
    promotedUserDataframes.value = []
    promotedUserFigures.value = []
    dataframeCount.value = 0
    tableRowCount.value = 0
    tableWindowStart.value = 0
    tableWindowEnd.value = 0
    tablePageOffsets.value = {}
    selectedTableArtifactsByWorkspace.value = {}
    selectedFigureArtifactsByWorkspace.value = {}
    dataPaneError.value = ''
    figureCount.value = 0
  }

  return {
    activeTurnArtifactRefreshKey,
    resultData,
    plotlyFigure,
    dataframes,
    figures,
    scalars,
    promotedUserDataframes,
    promotedUserFigures,
    dataframeCount,
    tableRowCount,
    tableWindowStart,
    tableWindowEnd,
    tablePageOffsets,
    selectedTableArtifactsByWorkspace,
    selectedFigureArtifactsByWorkspace,
    dataPaneError,
    figureCount,
    configurePersistence,
    setResultData,
    setPlotlyFigure,
    setDataframes,
    setFigures,
    setScalars,
    removeResultArtifact,
    setDataframeCount,
    setFigureCount,
    setDataPaneError,
    clearDataPaneError,
    setTableViewport,
    clearTableViewport,
    setTablePageOffset,
    getTablePageOffset,
    setSelectedTableArtifact,
    getSelectedTableArtifact,
    setSelectedFigureArtifact,
    getSelectedFigureArtifact,
    reset,
  }
})
