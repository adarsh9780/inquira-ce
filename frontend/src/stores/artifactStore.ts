import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useArtifactStore = defineStore('artifacts', () => {
  const activeTurnArtifactRefreshKey = ref(0)
  const resultData = ref<unknown>(null)
  const plotlyFigure = ref<unknown>(null)
  const dataframes = ref<unknown[]>([])
  const figures = ref<unknown[]>([])
  const scalars = ref<unknown[]>([])
  const promotedUserDataframes = ref<unknown[]>([])
  const promotedUserFigures = ref<unknown[]>([])
  const dataframeCount = ref(0)
  const tableRowCount = ref(0)
  const tableWindowStart = ref(0)
  const tableWindowEnd = ref(0)
  const tablePageOffsets = ref<Record<string, number>>({})
  const selectedTableArtifactsByWorkspace = ref<Record<string, string>>({})
  const selectedFigureArtifactsByWorkspace = ref<Record<string, string>>({})
  const dataPaneError = ref('')
  const figureCount = ref(0)

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
  }
})
