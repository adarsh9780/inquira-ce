<template>
  <div class="flex flex-col h-full">
    <!-- Figure Header (Teleported) -->
    <Teleport to="#workspace-right-pane-toolbar" v-if="isMounted && appStore.dataPane === 'figure'">
      <div class="flex items-center justify-end w-full gap-4">
        <div class="flex items-center space-x-3 text-sm mr-auto">
          <span v-if="appStore.isCodeRunning" class="text-xs px-2 py-1 rounded text-orange-600 bg-orange-100">
            Processing
          </span>
          <span v-else-if="isLoadingArtifacts || isLoadingFigure || isDeletingArtifact" class="text-xs px-2 py-1 rounded text-gray-700 bg-gray-100">
            {{ isDeletingArtifact ? 'Deleting chart...' : 'Loading charts...' }}
          </span>
          <span v-else-if="artifactListError" class="text-xs px-2 py-1 rounded text-red-700 bg-red-100">
            {{ artifactListError }}
          </span>
          <span v-else-if="selectedFigure" class="text-xs px-2 py-1 rounded text-purple-600 bg-purple-100">
            Chart Ready
          </span>
        </div>
        
        <div class="flex items-center space-x-2">
          <!-- Figure Selector -->
          <div v-if="orderedFigures && orderedFigures.length > 1" class="flex items-center">
            <HeaderDropdown
              id="figure-select"
              v-model="selectedArtifactId"
              :options="figureDropdownOptions"
              placeholder="Select figure"
              aria-label="Select figure"
              :fit-to-longest-label="true"
              max-width-class="min-w-[240px]"
            />
          </div>

          <!-- Delete Figure -->
          <button
            @click="deleteSelectedFigure"
            :disabled="!selectedArtifactId || isDeletingArtifact"
            class="inline-flex items-center px-3 py-1.5 border border-red-200 text-sm leading-4 font-medium rounded-md text-red-700 bg-red-50 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors"
            :class="(!selectedArtifactId || isDeletingArtifact) ? 'opacity-50 cursor-not-allowed' : ''"
          >
            <TrashIcon class="h-4 w-4 mr-1" />
            {{ isDeletingArtifact ? 'Deleting...' : 'Delete' }}
          </button>

          <!-- Download PNG Button -->
          <button
            @click="downloadPng"
            :disabled="!selectedFigure || isDownloading"
            class="inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
            :class="!selectedFigure ? 'opacity-50 cursor-not-allowed' : ''"
          >
            <PhotoIcon v-if="!isDownloading" class="h-4 w-4 mr-1" />
            <div v-else class="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600 mr-1"></div>
            {{ isDownloading ? 'Downloading...' : 'PNG' }}
          </button>
          
          <!-- Download HTML Button -->
          <button
            @click="downloadHtml"
            :disabled="!selectedFigure"
            class="inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
            :class="!selectedFigure ? 'opacity-50 cursor-not-allowed' : ''"
          >
            <DocumentIcon class="h-4 w-4 mr-1" />
            HTML
          </button>

          <!-- Fullscreen Button -->
          <button
            @click="toggleFullscreen"
            :disabled="!selectedFigure"
            class="inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
            :class="!selectedFigure ? 'opacity-50 cursor-not-allowed' : ''"
          >
            <ArrowsPointingOutIcon class="h-4 w-4 mr-1" />
            Fullscreen
          </button>
        </div>
      </div>
    </Teleport>
    
    <!-- Plotly Chart Container -->
    <div class="flex-1 relative mt-1">
      <div
        v-if="selectedFigure"
        :key="selectedArtifactId"
        ref="plotContainer"
        class="absolute inset-0 p-4"
      ></div>
      
      <!-- Empty State -->
      <div
        v-else
        class="absolute inset-0 flex items-center justify-center"
        style="background-color: var(--color-base);"
      >
        <div class="text-center">
          <ChartBarIcon class="h-12 w-12 mx-auto mb-3" style="color: var(--color-border);" />
          <p class="text-sm" style="color: var(--color-text-muted);">No chart to display</p>
          <p class="text-xs mt-1" style="color: var(--color-text-muted);">Run code that generates a Plotly figure</p>
        </div>
      </div>
    </div>
    
    <!-- Fullscreen Modal -->
    <div
      v-if="isFullscreen"
      class="fixed inset-0 z-50 bg-black bg-opacity-75 flex items-center justify-center"
      @click="closeFullscreen"
    >
      <div class="w-full h-full max-w-7xl max-h-full p-8">
        <div class="bg-white rounded-lg h-full flex flex-col">
          <div class="flex-shrink-0 flex items-center justify-between p-4 border-b">
            <h3 class="text-lg font-medium">Chart - Fullscreen View</h3>
            <button
              @click="closeFullscreen"
              class="text-gray-400 hover:text-gray-600"
            >
              <XMarkIcon class="h-6 w-6" />
            </button>
          </div>
          <div class="flex-1 relative">
            <div :key="selectedArtifactId" ref="fullscreenPlotContainer" class="absolute inset-0 p-4"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue'
import { useAppStore } from '../../stores/appStore'
import Plotly from 'plotly.js-dist-min'
import HeaderDropdown from '../ui/HeaderDropdown.vue'
import apiService from '../../services/apiService'
import { normalizePlotlyFigure } from '../../utils/figurePayload'
import { applyPlotlyTheme, applyPlotlyConfigTheme, PLOTLY_THEME_MODE } from '../../utils/plotlyTheme'
import { 
  PhotoIcon, 
  DocumentIcon, 
  ArrowsPointingOutIcon, 
  ChartBarIcon,
  XMarkIcon,
  TrashIcon
} from '@heroicons/vue/24/outline'

const appStore = useAppStore()

const plotContainer = ref(null)
let ro = null
const fullscreenPlotContainer = ref(null)
const isDownloading = ref(false)
const isFullscreen = ref(false)
const isLoadingArtifacts = ref(false)
const isLoadingFigure = ref(false)
const isDeletingArtifact = ref(false)
const selectedArtifactId = ref(null)
const isMounted = ref(false)
const workspaceFigureArtifacts = ref([])
const selectedFigurePayload = ref(null)
const artifactListError = ref('')
let listAbortController = null
let figureAbortController = null
const DEFAULT_PLOTLY_THEME_MODE = PLOTLY_THEME_MODE.SOFT

const orderedFigures = computed(() => {
  if (!Array.isArray(workspaceFigureArtifacts.value)) return []
  return workspaceFigureArtifacts.value
})

const figureDropdownOptions = computed(() => orderedFigures.value.map((fig, index) => ({
  value: fig.artifact_id,
  label: fig.logical_name || `Figure ${index + 1}`,
  key: fig.artifact_id || `${index}-figure`
})))

const selectedFigureMeta = computed(() => {
  if (!selectedArtifactId.value) return null
  return orderedFigures.value.find((fig) => fig.artifact_id === selectedArtifactId.value) || null
})

const selectedFigure = computed(() => normalizePlotlyFigure(selectedFigurePayload.value))

onMounted(async () => {
  isMounted.value = true
  // Observe container size changes to keep plot sized correctly
  if ('ResizeObserver' in window) {
    ro = new ResizeObserver(() => {
      if (plotContainer.value) {
        try { Plotly.Plots.resize(plotContainer.value) } catch (e) {}
      }
    })
  }
  if (plotContainer.value && ro) ro.observe(plotContainer.value)

  if (selectedFigure.value) {
    await renderPlot()
  }

  if (appStore.activeWorkspaceId) {
    await loadWorkspaceFigureArtifacts(appStore.activeWorkspaceId)
  }
})

onUnmounted(() => {
  listAbortController?.abort()
  figureAbortController?.abort()
  if (plotContainer.value) {
    Plotly.purge(plotContainer.value)
  }
  if (fullscreenPlotContainer.value) {
    Plotly.purge(fullscreenPlotContainer.value)
  }
  if (ro && plotContainer.value) {
    try { ro.unobserve(plotContainer.value) } catch (e) {}
  }
})

// Watch for selected figure changes
watch(() => selectedFigure.value, (newFigure) => {
  if (newFigure) {
    nextTick(() => {
      renderPlot()
    })
  }
})

watch(() => appStore.activeWorkspaceId, (workspaceId) => {
  selectedArtifactId.value = null
  selectedFigurePayload.value = null
  workspaceFigureArtifacts.value = []
  artifactListError.value = ''
  appStore.setFigureCount(0)
  if (workspaceId) {
    void loadWorkspaceFigureArtifacts(workspaceId)
  }
}, { immediate: true })

watch(
  () => (Array.isArray(appStore.figures) ? appStore.figures.map((fig) => String(fig?.artifact_id || fig?.name || '')).join('|') : ''),
  () => {
    if (!appStore.activeWorkspaceId) return
    void loadWorkspaceFigureArtifacts(appStore.activeWorkspaceId)
  }
)

watch(selectedArtifactId, (artifactId) => {
  void loadSelectedFigurePayload(artifactId)
})

// Re-render when the Figure pane becomes visible after being hidden by v-show
watch(() => appStore.dataPane, (pane) => {
  if (pane === 'figure' && appStore.activeWorkspaceId) {
    void loadWorkspaceFigureArtifacts(appStore.activeWorkspaceId)
  }
  if (pane === 'figure' && selectedFigure.value) {
    nextTick(() => {
      renderPlot()
    })
  }
})

async function loadWorkspaceFigureArtifacts(workspaceId) {
  const normalizedWorkspaceId = String(workspaceId || '').trim()
  if (!normalizedWorkspaceId) {
    workspaceFigureArtifacts.value = []
    selectedArtifactId.value = null
    selectedFigurePayload.value = null
    appStore.setFigureCount(0)
    return
  }
  listAbortController?.abort()
  listAbortController = new AbortController()
  isLoadingArtifacts.value = true
  artifactListError.value = ''
  try {
    const response = await apiService.v1ListWorkspaceArtifacts(
      normalizedWorkspaceId,
      'figure',
      { signal: listAbortController.signal },
    )
    const artifacts = Array.isArray(response?.artifacts) ? response.artifacts : []
    workspaceFigureArtifacts.value = artifacts
    appStore.setFigureCount(artifacts.length)

    if (!artifacts.length) {
      selectedArtifactId.value = null
      selectedFigurePayload.value = null
      appStore.setPlotlyFigure(null)
      return
    }
    const hasExistingSelection = artifacts.some((item) => item.artifact_id === selectedArtifactId.value)
    if (!hasExistingSelection) {
      selectedArtifactId.value = artifacts[0].artifact_id
    } else if (!selectedFigurePayload.value && selectedArtifactId.value) {
      await loadSelectedFigurePayload(selectedArtifactId.value)
    }
  } catch (error) {
    if (error?.name === 'AbortError') return
    console.warn('Failed to load workspace figure artifacts:', error)
    artifactListError.value = error?.message || 'Failed to load charts.'
    workspaceFigureArtifacts.value = []
    selectedArtifactId.value = null
    selectedFigurePayload.value = null
    appStore.setFigureCount(0)
  } finally {
    isLoadingArtifacts.value = false
  }
}

async function loadSelectedFigurePayload(artifactId) {
  const normalizedWorkspaceId = String(appStore.activeWorkspaceId || '').trim()
  const normalizedArtifactId = String(artifactId || '').trim()
  if (!normalizedWorkspaceId || !normalizedArtifactId) {
    selectedFigurePayload.value = null
    appStore.setPlotlyFigure(null)
    return
  }
  figureAbortController?.abort()
  figureAbortController = new AbortController()
  isLoadingFigure.value = true
  try {
    const metadata = await apiService.v1GetWorkspaceArtifactMetadata(
      normalizedWorkspaceId,
      normalizedArtifactId,
      { signal: figureAbortController.signal },
    )
    const figurePayload = normalizePlotlyFigure(metadata?.payload?.figure ?? metadata?.payload)
    if (!figurePayload) {
      throw new Error('Selected chart payload is unavailable.')
    }
    if (selectedArtifactId.value !== normalizedArtifactId) return
    selectedFigurePayload.value = figurePayload
    appStore.setPlotlyFigure(figurePayload)
  } catch (error) {
    if (error?.name === 'AbortError') return
    console.warn('Failed to load selected figure payload:', error)
    selectedFigurePayload.value = null
    appStore.setPlotlyFigure(null)
  } finally {
    isLoadingFigure.value = false
  }
}

async function waitForContainer(retries = 10) {
  while (retries-- > 0) {
    await nextTick()
    await new Promise(r => setTimeout(r, 50))
    const el = plotContainer.value
    if (el && el.clientWidth > 0 && el.clientHeight > 0) return true
  }
  return false
}

function resolvePlotThemeMode() {
  const appMode = String(appStore.plotlyThemeMode || '').trim().toLowerCase()
  if (appMode === PLOTLY_THEME_MODE.HARD) return PLOTLY_THEME_MODE.HARD
  return DEFAULT_PLOTLY_THEME_MODE
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

async function renderPlot() {
  if (!selectedFigure.value || !plotContainer.value) return

  // Ensure container has a measurable size
  const ready = await waitForContainer(12)
  if (!ready) return

  try {
    // Ensure container fills parent
    plotContainer.value.style.width = '100%'
    plotContainer.value.style.height = '100%'

    const rawFigureData = selectedFigure.value
    const themeMode = resolvePlotThemeMode()
    const figureData = applyPlotlyTheme(rawFigureData, { mode: themeMode, context: 'panel' }) || rawFigureData

    const layout = {
      ...(figureData.layout || {}),
      autosize: true,
      responsive: true,
    }

    const config = applyPlotlyConfigTheme(
      {
        displayModeBar: true,
        displaylogo: false,
        modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d'],
        responsive: true,
      },
      { mode: themeMode },
    )

    // Render (use newPlot for clean re-render)
    Plotly.purge(plotContainer.value)
    await Plotly.newPlot(plotContainer.value, figureData.data || [], layout, config)

    // Final resize pass once plotted
    requestAnimationFrame(() => {
      try { Plotly.Plots.resize(plotContainer.value) } catch (e) {}
    })

  } catch (error) {
    console.error('Failed to render plot:', error)
  }
}

async function renderFullscreenPlot() {
  if (!selectedFigure.value || !fullscreenPlotContainer.value) return

  try {
    const rawFigureData = selectedFigure.value
    const themeMode = resolvePlotThemeMode()
    const figureData = applyPlotlyTheme(rawFigureData, { mode: themeMode, context: 'fullscreen' }) || rawFigureData

    const layout = {
      ...(figureData.layout || {}),
      autosize: true,
      responsive: true,
    }

    const config = applyPlotlyConfigTheme(
      {
        displayModeBar: true,
        displaylogo: false,
        responsive: true,
      },
      { mode: themeMode },
    )

    await Plotly.newPlot(
      fullscreenPlotContainer.value,
      figureData.data || [],
      layout,
      config
    )
    
  } catch (error) {
    console.error('Failed to render fullscreen plot:', error)
  }
}

async function downloadPng() {
  if (!selectedFigure.value || !plotContainer.value || isDownloading.value) return

  isDownloading.value = true

  try {
    const logicalName = String(selectedFigureMeta.value?.logical_name || 'chart')
      .replace(/[^A-Za-z0-9._-]+/g, '_')
      .replace(/^_+|_+$/g, '') || 'chart'
    const filename = `${logicalName}_${new Date().toISOString().split('T')[0]}.png`

    await Plotly.downloadImage(plotContainer.value, {
      format: 'png',
      width: 1200,
      height: 800,
      filename: filename
    })

    console.debug('PNG downloaded successfully')

  } catch (error) {
    console.error('Failed to download PNG:', error)
  } finally {
    isDownloading.value = false
  }
}

async function downloadHtml() {
  if (!selectedFigure.value) return

  try {
    const rawFigureData = selectedFigure.value
    const themeMode = resolvePlotThemeMode()
    const figureData = applyPlotlyTheme(rawFigureData, { mode: themeMode, context: 'export' }) || rawFigureData
    const plotlyConfig = applyPlotlyConfigTheme({}, { mode: themeMode })
    const chartTitle = String(selectedFigureMeta.value?.logical_name || 'Chart Visualization')
    const escapedChartTitle = escapeHtml(chartTitle)
    
    const htmlContent = `<!DOCTYPE html>
<html>
<head>
    <title>${escapedChartTitle}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"><\/script>
    <style>
        body {
            margin: 0;
            padding: 20px;
            font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #FDFCF8;
            color: #27272A;
        }
        h1 { font-size: 1rem; margin: 0 0 12px 0; }
        #chart { width: 100%; height: calc(100vh - 84px); min-height: 600px; }
    </style>
</head>
<body>
    <h1>${escapedChartTitle}</h1>
    <div id="chart"></div>
    <script>
        Plotly.newPlot(
          'chart',
          ${JSON.stringify(figureData.data || [])},
          ${JSON.stringify(figureData.layout || {})},
          ${JSON.stringify(plotlyConfig)}
        );
    <\/script>
</body>
</html>`
    
    const blob = new Blob([htmlContent], { type: 'text/html;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    const logicalName = String(selectedFigureMeta.value?.logical_name || 'chart')
      .replace(/[^A-Za-z0-9._-]+/g, '_')
      .replace(/^_+|_+$/g, '') || 'chart'
    
    link.setAttribute('href', url)
    link.setAttribute('download', `${logicalName}_${new Date().toISOString().split('T')[0]}.html`)
    link.style.visibility = 'hidden'
    
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    console.debug('HTML downloaded successfully')
    
  } catch (error) {
    console.error('Failed to download HTML:', error)
  }
}

async function deleteSelectedFigure() {
  const workspaceId = String(appStore.activeWorkspaceId || '').trim()
  const artifactId = String(selectedArtifactId.value || '').trim()
  if (!workspaceId || !artifactId || isDeletingArtifact.value) return

  const logicalName = String(selectedFigureMeta.value?.logical_name || artifactId)
  const confirmed = window.confirm(`Delete chart "${logicalName}"? This cannot be undone.`)
  if (!confirmed) return

  isDeletingArtifact.value = true
  artifactListError.value = ''
  try {
    await apiService.v1DeleteWorkspaceArtifact(workspaceId, artifactId)
    await loadWorkspaceFigureArtifacts(workspaceId)
    const fallbackId = workspaceFigureArtifacts.value[0]?.artifact_id || null
    selectedArtifactId.value = fallbackId
    if (!fallbackId) {
      selectedFigurePayload.value = null
      appStore.setPlotlyFigure(null)
    }
  } catch (error) {
    if (error?.name === 'AbortError') return
    artifactListError.value = error?.message || 'Failed to delete chart.'
  } finally {
    isDeletingArtifact.value = false
  }
}

async function toggleFullscreen() {
  if (!selectedFigure.value) return

  isFullscreen.value = true

  await nextTick()
  await renderFullscreenPlot()
}

function closeFullscreen() {
  if (fullscreenPlotContainer.value) {
    Plotly.purge(fullscreenPlotContainer.value)
  }
  isFullscreen.value = false
}
</script>

<style scoped>
/* Plotly.js styling is handled by the library itself */
</style>
