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
        </div>
        
        <div class="flex items-center space-x-2">
          <!-- Figure Selector -->
          <div v-if="orderedFigures && orderedFigures.length > 1" class="flex min-w-0 items-center" style="max-width: min(42vw, 24rem);">
            <HeaderDropdown
              id="figure-select"
              v-model="selectedArtifactId"
              :options="figureDropdownOptions"
              placeholder="Select figure"
              aria-label="Select figure"
              :fit-to-longest-label="true"
              :min-chars="12"
              :max-chars="36"
              max-width-class="w-full"
            />
          </div>

          <!-- Delete Figure -->
          <button
            @click="deleteSelectedFigure"
            type="button"
            :disabled="!canDeleteSelectedFigure || isDeletingArtifact"
            class="inline-flex items-center px-3 py-1.5 border border-red-200 text-sm leading-4 font-medium rounded-md text-red-700 bg-red-50 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors"
            :class="(!canDeleteSelectedFigure || isDeletingArtifact) ? 'opacity-50 cursor-not-allowed' : ''"
          >
            <TrashIcon class="h-4 w-4 mr-1" />
            {{ isDeletingArtifact ? 'Deleting...' : 'Delete' }}
          </button>

          <!-- Export Menu -->
          <Menu as="div" class="relative inline-flex">
            <MenuButton
              :disabled="!selectedFigure || isDownloading"
              class="inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
              :class="(!selectedFigure || isDownloading) ? 'opacity-50 cursor-not-allowed' : ''"
            >
              <ArrowDownTrayIcon v-if="!isDownloading" class="h-4 w-4 mr-1.5" />
              <div v-else class="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600 mr-1.5"></div>
              <span>{{ isDownloading ? 'Exporting...' : 'Export' }}</span>
              <ChevronDownIcon class="h-4 w-4 ml-1.5" />
            </MenuButton>
            <transition
              enter-active-class="transition duration-100 ease-out"
              enter-from-class="opacity-0 scale-95 -translate-y-1"
              enter-to-class="opacity-100 scale-100 translate-y-0"
              leave-active-class="transition duration-75 ease-in"
              leave-from-class="opacity-100"
              leave-to-class="opacity-0"
            >
              <MenuItems
                class="absolute right-0 z-30 mt-9 min-w-[180px] overflow-hidden rounded-md border shadow-lg focus:outline-none"
                style="background-color: var(--color-surface); border-color: var(--color-border);"
              >
                <MenuItem v-slot="{ active }">
                  <button
                    type="button"
                    class="w-full text-left px-3 py-2 text-sm transition-colors"
                    :style="{
                      color: 'var(--color-text-main)',
                      backgroundColor: active ? 'color-mix(in srgb, var(--color-text-main) 7%, transparent)' : 'transparent'
                    }"
                    @click="downloadPng"
                  >
                    PNG image (.png)
                  </button>
                </MenuItem>
                <MenuItem v-slot="{ active }">
                  <button
                    type="button"
                    class="w-full text-left px-3 py-2 text-sm transition-colors"
                    :style="{
                      color: 'var(--color-text-main)',
                      backgroundColor: active ? 'color-mix(in srgb, var(--color-text-main) 7%, transparent)' : 'transparent'
                    }"
                    @click="downloadHtml"
                  >
                    HTML file (.html)
                  </button>
                </MenuItem>
              </MenuItems>
            </transition>
          </Menu>
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
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue'
import { Menu, MenuButton, MenuItem, MenuItems } from '@headlessui/vue'
import { useAppStore } from '../../stores/appStore'
import Plotly from 'plotly.js-dist-min'
import HeaderDropdown from '../ui/HeaderDropdown.vue'
import apiService from '../../services/apiService'
import { normalizePlotlyFigure } from '../../utils/figurePayload'
import { applyPlotlyTheme, applyPlotlyConfigTheme, PLOTLY_THEME_MODE } from '../../utils/plotlyTheme'
import { toast } from '../../composables/useToast'
import { 
  ArrowDownTrayIcon,
  ChevronDownIcon,
  ChartBarIcon,
  TrashIcon
} from '@heroicons/vue/24/outline'

const appStore = useAppStore()

const plotContainer = ref(null)
const MEMORY_FIGURE_PREFIX = 'memory:'
let ro = null
const isDownloading = ref(false)
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

function getMemoryFigureId(name, index = 0) {
  const normalizedName = String(name || '').trim() || `figure_${index + 1}`
  return `${MEMORY_FIGURE_PREFIX}${normalizedName}`
}

function isMemoryFigureId(artifactId) {
  return String(artifactId || '').startsWith(MEMORY_FIGURE_PREFIX)
}

const inMemoryFigureArtifacts = computed(() => {
  if (!Array.isArray(appStore.figures)) return []
  return appStore.figures
    .map((fig, index) => {
      const artifactId = String(fig?.artifact_id || fig?.data?.artifact_id || '').trim()
      if (artifactId) return null
      const normalizedFigure = normalizePlotlyFigure(fig?.data ?? fig)
      if (!normalizedFigure) return null
      const logicalName = String(fig?.logical_name || fig?.name || '').trim() || `Figure ${index + 1}`
      return {
        artifact_id: getMemoryFigureId(logicalName, index),
        logical_name: logicalName,
        source: 'memory',
        memory_figure: normalizedFigure,
      }
    })
    .filter(Boolean)
})

const orderedFigures = computed(() => {
  const persisted = Array.isArray(workspaceFigureArtifacts.value)
    ? workspaceFigureArtifacts.value.map((fig) => ({ ...fig, source: 'artifact' }))
    : []
  return [...persisted, ...inMemoryFigureArtifacts.value]
})

const figureDropdownOptions = computed(() => orderedFigures.value.map((fig, index) => ({
  value: fig.artifact_id,
  label: fig.source === 'memory'
    ? `${fig.logical_name || `Figure ${index + 1}`} (memory)`
    : (fig.logical_name || `Figure ${index + 1}`),
  key: fig.artifact_id || `${index}-figure`
})))

const selectedFigureMeta = computed(() => {
  if (!selectedArtifactId.value) return null
  return orderedFigures.value.find((fig) => fig.artifact_id === selectedArtifactId.value) || null
})

const canDeleteSelectedFigure = computed(() => selectedFigureMeta.value?.source === 'artifact')

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

  if (appStore.activeWorkspaceId && appStore.hasWorkspace) {
    await loadWorkspaceFigureArtifacts(appStore.activeWorkspaceId)
  }
})

onUnmounted(() => {
  listAbortController?.abort()
  figureAbortController?.abort()
  if (plotContainer.value) {
    Plotly.purge(plotContainer.value)
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
  if (workspaceId && appStore.hasWorkspace) {
    void loadWorkspaceFigureArtifacts(workspaceId)
  }
}, { immediate: true })

watch(orderedFigures, (figures) => {
  appStore.setFigureCount(Array.isArray(figures) ? figures.length : 0)
  if (selectedArtifactId.value && !orderedFigures.value.some((fig) => fig.artifact_id === selectedArtifactId.value)) {
    selectedArtifactId.value = orderedFigures.value[0]?.artifact_id || null
  }
}, { immediate: true })

watch(
  () => (
    Array.isArray(appStore.figures)
      ? appStore.figures
        .map((fig) => String(fig?.artifact_id || fig?.data?.artifact_id || fig?.name || ''))
        .join('|')
      : ''
  ),
  () => {
    if (!appStore.activeWorkspaceId || !appStore.hasWorkspace) return
    const latestFigureHint = resolveLatestFigureHint()
    void loadWorkspaceFigureArtifacts(appStore.activeWorkspaceId, {
      preferredArtifactId: latestFigureHint.artifactId,
      preferredLogicalName: latestFigureHint.logicalName,
    })
  }
)

watch(selectedArtifactId, (artifactId) => {
  const normalizedWorkspaceId = String(appStore.activeWorkspaceId || '').trim()
  if (normalizedWorkspaceId) {
    appStore.setSelectedFigureArtifact(normalizedWorkspaceId, String(artifactId || '').trim())
  }
  void loadSelectedFigurePayload(artifactId)
})

// Re-render when the Figure pane becomes visible after being hidden by v-show
watch(() => appStore.dataPane, (pane) => {
  if (pane === 'figure' && appStore.activeWorkspaceId && appStore.hasWorkspace) {
    const latestFigureHint = resolveLatestFigureHint()
    void loadWorkspaceFigureArtifacts(appStore.activeWorkspaceId, {
      preferredArtifactId: latestFigureHint.artifactId,
      preferredLogicalName: latestFigureHint.logicalName,
    })
  }
  if (pane === 'figure' && selectedFigure.value) {
    nextTick(() => {
      renderPlot()
    })
  }
})

function resolveLatestFigureHint() {
  const latest = Array.isArray(appStore.figures) ? appStore.figures[0] : null
  if (!latest || typeof latest !== 'object') {
    return { artifactId: '', logicalName: '' }
  }
  return {
    artifactId: String(latest?.artifact_id || latest?.data?.artifact_id || '').trim()
      || getMemoryFigureId(latest?.logical_name || latest?.name || latest?.data?.name || ''),
    logicalName: String(latest?.logical_name || latest?.name || latest?.data?.name || '').trim(),
  }
}

function pickPreferredArtifactId(artifacts, preferredArtifactId, preferredLogicalName) {
  if (!Array.isArray(artifacts) || artifacts.length === 0) return null

  const normalizedPreferredId = String(preferredArtifactId || '').trim()
  if (normalizedPreferredId) {
    const direct = artifacts.find((item) => item.artifact_id === normalizedPreferredId)
    if (direct?.artifact_id) return direct.artifact_id
  }

  const normalizedPreferredLogicalName = String(preferredLogicalName || '').trim().toLowerCase()
  if (normalizedPreferredLogicalName) {
    const logicalMatch = artifacts.find((item) => {
      const logicalName = String(item?.logical_name || '').trim().toLowerCase()
      const artifactId = String(item?.artifact_id || '').trim().toLowerCase()
      return logicalName === normalizedPreferredLogicalName || artifactId === normalizedPreferredLogicalName
    })
    if (logicalMatch?.artifact_id) return logicalMatch.artifact_id
  }

  return null
}

function resolveRememberedFigureArtifactId(workspaceId, candidates) {
  const rememberedArtifactId = String(appStore.getSelectedFigureArtifact(workspaceId) || '').trim()
  if (!rememberedArtifactId) return null
  return candidates.some((item) => item.artifact_id === rememberedArtifactId) ? rememberedArtifactId : null
}

async function loadWorkspaceFigureArtifacts(workspaceId, options = {}) {
  const normalizedWorkspaceId = String(workspaceId || '').trim()
  if (!normalizedWorkspaceId || !appStore.hasWorkspace) {
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

    const candidates = orderedFigures.value
    if (!candidates.length) {
      selectedArtifactId.value = null
      selectedFigurePayload.value = null
      appStore.setPlotlyFigure(null)
      return
    }

    const preferredArtifactId = pickPreferredArtifactId(
      candidates,
      options?.preferredArtifactId,
      options?.preferredLogicalName,
    )
    const rememberedArtifactId = resolveRememberedFigureArtifactId(
      normalizedWorkspaceId,
      candidates,
    )

    const hasExistingSelection = candidates.some((item) => item.artifact_id === selectedArtifactId.value)
    const nextSelection = preferredArtifactId
      || rememberedArtifactId
      || (hasExistingSelection ? selectedArtifactId.value : null)
      || candidates[0].artifact_id

    if (nextSelection !== selectedArtifactId.value) {
      selectedArtifactId.value = nextSelection
    } else if (selectedArtifactId.value && (isMemoryFigureId(selectedArtifactId.value) || !selectedFigurePayload.value)) {
      await loadSelectedFigurePayload(selectedArtifactId.value)
    }
  } catch (error) {
    if (error?.name === 'AbortError') return
    console.warn('Failed to load workspace figure artifacts:', error)
    artifactListError.value = error?.message || 'Failed to load charts.'
    workspaceFigureArtifacts.value = []
    const fallbackSelection = orderedFigures.value[0]?.artifact_id || null
    selectedArtifactId.value = fallbackSelection
    if (!fallbackSelection) {
      selectedFigurePayload.value = null
      appStore.setPlotlyFigure(null)
      appStore.setFigureCount(0)
    }
  } finally {
    isLoadingArtifacts.value = false
  }
}

async function loadSelectedFigurePayload(artifactId) {
  const normalizedWorkspaceId = String(appStore.activeWorkspaceId || '').trim()
  const normalizedArtifactId = String(artifactId || '').trim()
  if (!normalizedWorkspaceId || !normalizedArtifactId || !appStore.hasWorkspace) {
    selectedFigurePayload.value = null
    appStore.setPlotlyFigure(null)
    return
  }
  figureAbortController?.abort()
  figureAbortController = new AbortController()
  isLoadingFigure.value = true
  try {
    if (isMemoryFigureId(normalizedArtifactId)) {
      const memoryFigure = orderedFigures.value.find((fig) => fig.artifact_id === normalizedArtifactId && fig.source === 'memory')
      const figurePayload = normalizePlotlyFigure(memoryFigure?.memory_figure)
      if (!figurePayload) {
        throw new Error('Selected chart payload is unavailable.')
      }
      if (selectedArtifactId.value !== normalizedArtifactId) return
      selectedFigurePayload.value = figurePayload
      appStore.setPlotlyFigure(figurePayload)
      return
    }

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

function getExportBaseName() {
  const logicalName = String(selectedFigureMeta.value?.logical_name || 'chart')
    .replace(/[^A-Za-z0-9._-]+/g, '_')
    .replace(/^_+|_+$/g, '')
  return logicalName || 'chart'
}

function decodeBase64ToBytes(base64Text) {
  const raw = atob(String(base64Text || ''))
  const bytes = new Uint8Array(raw.length)
  for (let i = 0; i < raw.length; i += 1) {
    bytes[i] = raw.charCodeAt(i)
  }
  return bytes
}

async function persistExportFile({
  defaultFileName,
  mimeType,
  payload,
  tauriFilters,
  browserFileTypes
}) {
  if (window.__TAURI_INTERNALS__) {
    const { save } = await import('@tauri-apps/plugin-dialog')
    const savePath = await save({
      defaultPath: defaultFileName,
      filters: Array.isArray(tauriFilters) ? tauriFilters : []
    })
    if (!savePath) return false
    const { writeFile } = await import('@tauri-apps/plugin-fs')
    await writeFile(savePath, payload)
    return true
  }

  if (typeof window.showSaveFilePicker === 'function') {
    try {
      const handle = await window.showSaveFilePicker({
        suggestedName: defaultFileName,
        types: Array.isArray(browserFileTypes) ? browserFileTypes : []
      })
      const writable = await handle.createWritable()
      await writable.write(payload)
      await writable.close()
      return true
    } catch (error) {
      if (error?.name === 'AbortError') return false
      throw error
    }
  }

  const blobData = payload instanceof Uint8Array ? payload : new TextEncoder().encode(String(payload || ''))
  const blob = new Blob([blobData], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.setAttribute('href', url)
  link.setAttribute('download', defaultFileName)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  return true
}

async function downloadPng() {
  if (!selectedFigure.value || !plotContainer.value || isDownloading.value) return

  isDownloading.value = true

  try {
    const filename = `${getExportBaseName()}_${new Date().toISOString().split('T')[0]}.png`
    const dataUrl = await Plotly.toImage(plotContainer.value, {
      format: 'png',
      width: 1200,
      height: 800
    })
    const encoded = String(dataUrl || '')
    const base64 = encoded.includes(',') ? encoded.split(',')[1] : encoded
    const bytes = decodeBase64ToBytes(base64)
    const exported = await persistExportFile({
      defaultFileName: filename,
      mimeType: 'image/png',
      payload: bytes,
      tauriFilters: [{ name: 'PNG Image', extensions: ['png'] }],
      browserFileTypes: [{ description: 'PNG Image', accept: { 'image/png': ['.png'] } }]
    })
    if (exported) toast.success('Export complete', 'Chart saved as PNG.')
  } catch (error) {
    console.error('Failed to download PNG:', error)
    toast.error('Export failed', 'Unable to save PNG file.')
  } finally {
    isDownloading.value = false
  }
}

async function downloadHtml() {
  if (!selectedFigure.value || isDownloading.value) return

  isDownloading.value = true

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

    const filename = `${getExportBaseName()}_${new Date().toISOString().split('T')[0]}.html`
    const bytes = new TextEncoder().encode(htmlContent)
    const exported = await persistExportFile({
      defaultFileName: filename,
      mimeType: 'text/html',
      payload: bytes,
      tauriFilters: [{ name: 'HTML File', extensions: ['html'] }],
      browserFileTypes: [{ description: 'HTML File', accept: { 'text/html': ['.html'] } }]
    })
    if (exported) toast.success('Export complete', 'Chart saved as HTML.')
  } catch (error) {
    console.error('Failed to download HTML:', error)
    toast.error('Export failed', 'Unable to save HTML file.')
  } finally {
    isDownloading.value = false
  }
}

async function resolveConfirmation(message) {
  try {
    const decision = window.confirm(message)
    if (decision && typeof decision.then === 'function') {
      return Boolean(await decision)
    }
    return Boolean(decision)
  } catch (_error) {
    return false
  }
}

async function deleteSelectedFigure() {
  const workspaceId = String(appStore.activeWorkspaceId || '').trim()
  const artifactId = String(selectedArtifactId.value || '').trim()
  if (!workspaceId || !artifactId || isDeletingArtifact.value) return
  if (isMemoryFigureId(artifactId)) return

  const logicalName = String(selectedFigureMeta.value?.logical_name || artifactId)
  const confirmed = await resolveConfirmation(`Delete chart "${logicalName}"? This cannot be undone.`)
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

</script>

<style scoped>
/* Plotly.js styling is handled by the library itself */
</style>
