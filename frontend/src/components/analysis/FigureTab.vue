<template>
  <div class="flex flex-col h-full">
    <Teleport to="#workspace-right-pane-toolbar-center" v-if="isMounted && uiStore.dataPane === 'figure'">
      <div v-if="figureDropdownOptions.length > 0" class="flex min-w-[11rem] max-w-full items-center" style="width: clamp(11rem, 28vw, 19rem);">
        <HeaderDropdown
          id="figure-select"
          v-model="selectedArtifactId"
          :options="figureDropdownOptions"
          placeholder="Select chart"
          aria-label="Select chart"
          max-width-class="w-full"
        />
      </div>
    </Teleport>

    <Teleport to="#workspace-right-pane-toolbar-right" v-if="isMounted && uiStore.dataPane === 'figure'">
      <div class="flex min-w-0 items-center justify-end w-full gap-3">
        <div class="flex min-w-0 items-center space-x-3 text-sm">
          <span
            v-if="isLoadingArtifacts || isLoadingFigure || isDeletingArtifact"
            class="rounded px-2 py-1 text-xs"
            style="background-color: var(--color-panel-muted); color: var(--color-text-main);"
          >
            {{ isDeletingArtifact ? 'Deleting chart...' : 'Loading charts...' }}
          </span>
        </div>

        <div class="flex min-w-0 items-center justify-end gap-2">
          <button
            ref="exportMenuButtonRef"
            type="button"
            :disabled="!selectedFigure || isDownloading"
            class="btn-icon h-8 w-8 shrink-0 border"
            style="border-color: var(--color-border); color: var(--color-text-muted);"
            :class="(!selectedFigure || isDownloading) ? 'opacity-50 cursor-not-allowed' : ''"
            :title="isDownloading ? 'Exporting chart' : 'Export chart'"
            :aria-label="isDownloading ? 'Exporting chart' : 'Export chart'"
            @click="toggleExportMenu"
          >
            <ArrowDownTrayIcon v-if="!isDownloading" class="h-4 w-4" />
            <div
              v-else
              class="h-4 w-4 animate-spin rounded-full border-2"
              style="border-color: var(--color-border); border-top-color: var(--color-text-main);"
            ></div>
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
        class="plotly-surface absolute inset-0 p-4"
      ></div>

      <!-- Empty State -->
      <div v-else class="absolute inset-0" style="background-color: var(--color-base);">
        <AppEmptyState
          :title="artifactListError ? 'Charts unavailable' : 'No saved charts'"
          :description="artifactListError || 'Ask AI for a chart, or promote one from Runs.'"
        ><template #icon><ChartBarIcon class="h-7 w-7" /></template></AppEmptyState>
      </div>
    </div>
  </div>

  <ConfirmationModal
    :is-open="isDeleteDialogOpen"
    title="Delete Chart"
    :message="deleteDialogMessage"
    confirm-text="Delete"
    cancel-text="Cancel"
    @close="closeDeleteDialog"
    @confirm="deleteSelectedFigure"
  />
  <FloatingActionMenu
    :is-open="exportMenuOpen"
    :position="exportMenuPosition"
    :items="exportMenuItems"
    marker-attr="data-figure-export-menu"
    width-class="w-48"
    :width="192"
    :height="136"
    @select="handleExportMenuSelect"
    @close="exportMenuOpen = false"
  />
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue'
import { useUiStore } from '../../stores/uiStore'
import { usePreferencesStore } from '../../stores/preferencesStore'
import { useArtifactStore } from '../../stores/artifactStore'
import { useExecutionStore } from '../../stores/executionStore'
import { useWorkspaceStore } from '../../stores/workspaceStore'
import { useConversationStore } from '../../stores/conversationStore'
import { useWorkspaceActivation } from '../../composables/useWorkspaceActivation'
import { useArtifactPresentation } from '../../composables/useArtifactPresentation'
import HeaderDropdown from '../ui/HeaderDropdown.vue'
import ConfirmationModal from '../modals/ConfirmationModal.vue'
import FloatingActionMenu from '../ui/FloatingActionMenu.vue'
import AppEmptyState from '../ui/AppEmptyState.vue'
import { artifactApi } from '../../api/artifacts'
import { normalizePlotlyFigure } from '../../utils/figurePayload'
import { loadPlotly } from '../../utils/loadPlotly'
import { persistExportFile } from '../../utils/exportFile'
import { applyPlotlyTheme, applyPlotlyConfigTheme, PLOTLY_THEME_MODE } from '../../utils/plotlyTheme'
import { toast } from '../../composables/useToast'
import {
  ArrowDownTrayIcon,
  ChartBarIcon,
} from '@heroicons/vue/24/outline'

const uiStore = useUiStore()
const preferencesStore = usePreferencesStore()
const artifactStore = useArtifactStore()
const executionStore = useExecutionStore()
const workspaceStore = useWorkspaceStore()
const conversationStore = useConversationStore()
const workspaceActivation = useWorkspaceActivation()
const artifactPresentation = useArtifactPresentation()

const plotContainer = ref<any>(null)
let ro: ResizeObserver | null = null
const isDownloading = ref(false)
const isLoadingArtifacts = ref(false)
const isLoadingFigure = ref(false)
const isDeletingArtifact = ref(false)
const isDeleteDialogOpen = ref(false)
const selectedArtifactId = ref<any>(null)
const isMounted = ref(false)
const workspaceFigureArtifacts = ref<any[]>([])
const selectedFigurePayload = ref<any>(null)
const artifactListError = ref('')
const exportMenuOpen = ref(false)
const exportMenuButtonRef = ref<any>(null)
const exportMenuPosition = ref({ x: 0, y: 0 })
let listAbortController: AbortController | null = null
let figureAbortController: AbortController | null = null
let plotly: any = null

const exportMenuItems = computed(() => [
  { id: 'png', label: 'PNG image (.png)' },
  { id: 'html', label: 'HTML file (.html)' },
  { id: 'delete', label: 'Delete chart', dividerBefore: true, destructive: true, disabled: !canDeleteSelectedFigure.value || isDeletingArtifact.value },
])

const persistedFigureArtifacts = computed(() => (
  Array.isArray(workspaceFigureArtifacts.value) ? workspaceFigureArtifacts.value : []
))

const liveFigureArtifacts = computed(() => {
  const persistedIds = new Set(
    persistedFigureArtifacts.value
      .map((fig) => String(fig?.artifact_id || '').trim())
      .filter(Boolean),
  )
  const conversationId = String(conversationStore.activeConversationId || '').trim()
  const workspaceId = String(workspaceStore.activeWorkspaceId || '').trim()
  const scopeKey = conversationId ? `conversation:${conversationId}` : `workspace:${workspaceId || 'unscoped'}`
  const userRevisions = (Array.isArray(artifactStore.promotedUserFigures) ? artifactStore.promotedUserFigures : [])
    .filter((item: any) => String(item?.scopeKey || '') === scopeKey)
  return [...userRevisions, ...(Array.isArray(artifactStore.figures) ? artifactStore.figures : [])]
    .map((fig, index) => {
      const figurePayload = normalizePlotlyFigure(fig?.data ?? fig)
      if (!figurePayload) return null
      const artifactId = String(fig?.artifact_id || figurePayload?.artifact_id || `live-figure-${index + 1}`).trim()
      if (!artifactId || persistedIds.has(artifactId)) return null
      const logicalName = String(fig?.logical_name || figurePayload?.logical_name || fig?.name || `figure_${index + 1}`).trim()
      return {
        ...(fig || {}),
        artifact_id: artifactId,
        logical_name: logicalName,
        display_name: String(fig?.display_name || logicalName).trim(),
        data: figurePayload,
        source: fig?.promoted ? 'revision' : 'live',
      }
    })
    .filter(Boolean)
})

const orderedFigures = computed(() => {
  const persisted = persistedFigureArtifacts.value.map((fig) => ({ ...fig, source: 'artifact' }))
  return [...liveFigureArtifacts.value, ...persisted]
})

const figureDropdownOptions = computed(() => orderedFigures.value.map((figure, index) => ({
  value: figure.artifact_id,
  label: figure.display_name || figure.logical_name || `Chart ${index + 1}`,
  key: figure.artifact_id,
})))

const selectedFigureMeta = computed(() => {
  if (!selectedArtifactId.value) return null
  return orderedFigures.value.find((fig) => fig.artifact_id === selectedArtifactId.value) || null
})

const canDeleteSelectedFigure = computed(() => selectedFigureMeta.value?.source === 'artifact')
const deleteDialogMessage = computed(() => {
  const artifactId = String(selectedArtifactId.value || '').trim()
  if (!artifactId) return 'Delete this chart? This cannot be undone.'
  const logicalName = String(selectedFigureMeta.value?.display_name || selectedFigureMeta.value?.logical_name || artifactId)
  return `Delete chart "${logicalName}"? This cannot be undone.`
})

const selectedFigure = computed(() => normalizePlotlyFigure(selectedFigurePayload.value))

function updateExportMenuPosition() {
  const rect = exportMenuButtonRef.value?.getBoundingClientRect?.()
  if (!rect) return
  exportMenuPosition.value = {
    x: rect.right - 192,
    y: rect.bottom + 8,
  }
}

function toggleExportMenu() {
  if (!selectedFigure.value || isDownloading.value) return
  updateExportMenuPosition()
  exportMenuOpen.value = !exportMenuOpen.value
}

function handleExportMenuSelect(action: any) {
  if (action === 'png') void downloadPng()
  if (action === 'html') void downloadHtml()
  if (action === 'delete') openDeleteDialog()
}

onMounted(async () => {
  isMounted.value = true
  // Observe container size changes to keep plot sized correctly
  if ('ResizeObserver' in window) {
    ro = new ResizeObserver(() => {
      if (plotContainer.value) {
        try { plotly?.Plots.resize(plotContainer.value) } catch (e) {}
      }
    })
  }
  if (plotContainer.value && ro) ro.observe(plotContainer.value)

  if (selectedFigure.value) {
    await renderPlot()
  }

  if (conversationStore.activeConversationId && conversationStore.activeTurnId && workspaceStore.hasWorkspace) {
    await loadActiveTurnFigureArtifacts()
  }
})

onUnmounted(() => {
  listAbortController?.abort()
  figureAbortController?.abort()
  if (plotContainer.value) {
    plotly?.purge(plotContainer.value)
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

watch(() => workspaceStore.activeWorkspaceId, () => {
  selectedArtifactId.value = null
  selectedFigurePayload.value = null
  workspaceFigureArtifacts.value = []
  artifactListError.value = ''
}, { immediate: true })

watch(
  () => [
    String(conversationStore.activeConversationId || '').trim(),
    String(conversationStore.activeTurnId || '').trim(),
    String(artifactStore.activeTurnArtifactRefreshKey || 0),
  ].join('||'),
  async () => {
    if (!workspaceStore.hasWorkspace) return

    const previousSelection = String(selectedArtifactId.value || '').trim()
    await loadActiveTurnFigureArtifacts()

    const nextSelection = String(selectedArtifactId.value || '').trim()
    if (!nextSelection || nextSelection !== previousSelection) return
    await loadSelectedFigurePayload(nextSelection)
  },
)

watch(orderedFigures, (figures) => {
  artifactStore.setFigureCount(Array.isArray(figures) ? figures.length : 0)
  const workspaceId = String(workspaceStore.activeWorkspaceId || '').trim()
  const preferredArtifactId = workspaceId ? artifactStore.getSelectedFigureArtifact(workspaceId) : ''
  if (
    preferredArtifactId
    && preferredArtifactId !== selectedArtifactId.value
    && orderedFigures.value.some((fig) => fig.artifact_id === preferredArtifactId)
  ) {
    selectedArtifactId.value = preferredArtifactId
    return
  }
  if (!selectedArtifactId.value && orderedFigures.value.length > 0) {
    selectedArtifactId.value = orderedFigures.value[0]?.artifact_id || null
    return
  }
  if (selectedArtifactId.value && !orderedFigures.value.some((fig) => fig.artifact_id === selectedArtifactId.value)) {
    selectedArtifactId.value = orderedFigures.value[0]?.artifact_id || null
  }
}, { immediate: true })

watch(
  () => artifactStore.getSelectedFigureArtifact(workspaceStore.activeWorkspaceId),
  (preferredArtifactId) => {
    const normalizedArtifactId = String(preferredArtifactId || '').trim()
    if (
      normalizedArtifactId
      && normalizedArtifactId !== String(selectedArtifactId.value || '').trim()
      && orderedFigures.value.some((item) => String(item?.artifact_id || '').trim() === normalizedArtifactId)
    ) {
      selectedArtifactId.value = normalizedArtifactId
    }
  },
)

watch(selectedArtifactId, (artifactId) => {
  const normalizedWorkspaceId = String(workspaceStore.activeWorkspaceId || '').trim()
  if (normalizedWorkspaceId) {
    artifactStore.setSelectedFigureArtifact(normalizedWorkspaceId, String(artifactId || '').trim())
  }
  void loadSelectedFigurePayload(artifactId)
})

// Re-render when the Figure pane becomes visible after being hidden by v-show
watch(() => uiStore.dataPane, (pane) => {
  if (pane === 'figure' && conversationStore.activeConversationId && conversationStore.activeTurnId && workspaceStore.hasWorkspace) {
    void loadActiveTurnFigureArtifacts()
  }
  if (pane === 'figure' && selectedFigure.value) {
    nextTick(() => {
      renderPlot()
    })
  }
})

watch(
  () => preferencesStore.uiTheme,
  async () => {
    if (!selectedFigure.value || uiStore.dataPane !== 'figure') return
    await nextTick()
    await renderPlot()
  },
)

async function loadActiveTurnFigureArtifacts() {
  const conversationId = String(conversationStore.activeConversationId || '').trim()
  const turnId = String(conversationStore.activeTurnId || '').trim()
  if (!conversationId || !turnId || !workspaceStore.hasWorkspace) {
    workspaceFigureArtifacts.value = []
    selectedArtifactId.value = liveFigureArtifacts.value[0]?.artifact_id || null
    selectedFigurePayload.value = liveFigureArtifacts.value[0]?.data || null
    artifactStore.setFigureCount(liveFigureArtifacts.value.length)
    return
  }
  listAbortController?.abort()
  listAbortController = new AbortController()
  isLoadingArtifacts.value = true
  artifactListError.value = ''
  try {
    const response: any = await artifactApi.listTurn(
      conversationId,
      turnId,
      'figure',
      { signal: listAbortController.signal },
    )
    const artifacts = Array.isArray(response?.artifacts) ? response.artifacts : []
    workspaceFigureArtifacts.value = artifacts
    artifactStore.setFigureCount(orderedFigures.value.length)

    const candidates = orderedFigures.value
    if (!candidates.length) {
      selectedArtifactId.value = null
      selectedFigurePayload.value = null
      artifactStore.setPlotlyFigure(null)
      return
    }

    const hasExistingSelection = candidates.some((item) => item.artifact_id === selectedArtifactId.value)
    const nextSelection = (hasExistingSelection ? selectedArtifactId.value : null)
      || candidates[0].artifact_id

    if (nextSelection !== selectedArtifactId.value) {
      selectedArtifactId.value = nextSelection
    } else if (selectedArtifactId.value && !selectedFigurePayload.value) {
      await loadSelectedFigurePayload(selectedArtifactId.value)
    }
  } catch (error: any) {
    if (error?.name === 'AbortError') return
    console.warn('Failed to load active turn figure artifacts:', error)
    artifactListError.value = error?.message || 'Failed to load charts.'
    workspaceFigureArtifacts.value = []
    selectedArtifactId.value = null
    selectedFigurePayload.value = null
    artifactStore.setPlotlyFigure(null)
    artifactStore.setFigureCount(0)
  } finally {
    isLoadingArtifacts.value = false
  }
}

async function loadSelectedFigurePayload(artifactId: any) {
  const conversationId = String(conversationStore.activeConversationId || '').trim()
  const turnId = String(conversationStore.activeTurnId || '').trim()
  const normalizedArtifactId = String(artifactId || '').trim()
  if (!normalizedArtifactId || !workspaceStore.hasWorkspace) {
    selectedFigurePayload.value = null
    artifactStore.setPlotlyFigure(null)
    return
  }
  const liveFigure = liveFigureArtifacts.value.find(
    (fig) => String(fig?.artifact_id || '').trim() === normalizedArtifactId,
  )
  if (liveFigure) {
    selectedFigurePayload.value = liveFigure.data
    artifactStore.setPlotlyFigure(liveFigure.data)
    return
  }
  if (!conversationId || !turnId) {
    selectedFigurePayload.value = null
    artifactStore.setPlotlyFigure(null)
    return
  }
  figureAbortController?.abort()
  figureAbortController = new AbortController()
  isLoadingFigure.value = true
  try {
    const metadata: any = await artifactApi.metadata(
      conversationId,
      turnId,
      normalizedArtifactId,
      { signal: figureAbortController.signal },
    )
    const figurePayload = normalizePlotlyFigure(metadata?.payload?.figure ?? metadata?.payload)
    if (!figurePayload) {
      throw new Error('Selected chart payload is unavailable.')
    }
    if (selectedArtifactId.value !== normalizedArtifactId) return
    selectedFigurePayload.value = figurePayload
    artifactStore.setPlotlyFigure(figurePayload)
  } catch (error: any) {
    if (error?.name === 'AbortError') return
    console.warn('Failed to load selected figure payload:', error)
    selectedFigurePayload.value = null
    artifactStore.setPlotlyFigure(null)
    artifactListError.value = error?.message || 'Failed to load selected chart.'
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

function escapeHtml(value: any) {
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
    plotly = await loadPlotly()
    // Ensure container fills parent
    plotContainer.value.style.width = '100%'
    plotContainer.value.style.height = '100%'

    const rawFigureData = selectedFigure.value
    const themeMode = PLOTLY_THEME_MODE.SOFT
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
    plotly.purge(plotContainer.value)
    await plotly.newPlot(plotContainer.value, figureData.data || [], layout, config)

    // Final resize pass once plotted
    requestAnimationFrame(() => {
      try { plotly?.Plots.resize(plotContainer.value) } catch (e) {}
    })

  } catch (error: any) {
    console.error('Failed to render plot:', error)
  }
}

function getExportBaseName() {
  const logicalName = String(selectedFigureMeta.value?.logical_name || selectedFigureMeta.value?.display_name || 'chart')
    .replace(/[^A-Za-z0-9._-]+/g, '_')
    .replace(/^_+|_+$/g, '')
  return logicalName || 'chart'
}

function decodeBase64ToBytes(base64Text: any) {
  const raw = atob(String(base64Text || ''))
  const bytes = new Uint8Array(raw.length)
  for (let i = 0; i < raw.length; i += 1) {
    bytes[i] = raw.charCodeAt(i)
  }
  return bytes
}

async function downloadPng() {
  if (!selectedFigure.value || !plotContainer.value || isDownloading.value) return

  isDownloading.value = true

  try {
    plotly = await loadPlotly()
    const filename = `${getExportBaseName()}_${new Date().toISOString().split('T')[0]}.png`
    const dataUrl = await plotly.toImage(plotContainer.value, {
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
      nativeFilters: [{ name: 'PNG Image', extensions: ['png'] }],
      browserFileTypes: [{ description: 'PNG Image', accept: { 'image/png': ['.png'] } }]
    })
    if (exported) toast.success('Export complete', 'Chart saved as PNG.')
  } catch (error: any) {
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
    const themeMode = PLOTLY_THEME_MODE.SOFT
    const figureData = applyPlotlyTheme(rawFigureData, { mode: themeMode, context: 'export' }) || rawFigureData
    const plotlyConfig = applyPlotlyConfigTheme({}, { mode: themeMode })
    const chartTitle = String(selectedFigureMeta.value?.display_name || selectedFigureMeta.value?.logical_name || 'Chart Visualization')
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
            font-family: var(--font-ui);
            background: var(--color-base);
            color: var(--color-text-main);
        }
        h1 { font-size: 1rem; margin: 0 0 12px 0; }
        #chart { width: 100%; height: calc(100vh - 84px); min-height: 600px; }
    </style>
</head>
<body>
    <h1>${escapedChartTitle}</h1>
    <div id="chart"></div>
    <script lang="ts">
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
      nativeFilters: [{ name: 'HTML File', extensions: ['html'] }],
      browserFileTypes: [{ description: 'HTML File', accept: { 'text/html': ['.html'] } }]
    })
    if (exported) toast.success('Export complete', 'Chart saved as HTML.')
  } catch (error: any) {
    console.error('Failed to download HTML:', error)
    toast.error('Export failed', 'Unable to save HTML file.')
  } finally {
    isDownloading.value = false
  }
}

function openDeleteDialog() {
  if (!canDeleteSelectedFigure.value || isDeletingArtifact.value) return
  isDeleteDialogOpen.value = true
}

function closeDeleteDialog() {
  if (isDeletingArtifact.value) return
  isDeleteDialogOpen.value = false
}

async function deleteSelectedFigure() {
  const conversationId = String(conversationStore.activeConversationId || '').trim()
  const turnId = String(conversationStore.activeTurnId || '').trim()
  const artifactId = String(selectedArtifactId.value || '').trim()
  if (!conversationId || !turnId || !artifactId || isDeletingArtifact.value) return

  isDeleteDialogOpen.value = false
  isDeletingArtifact.value = true
  artifactListError.value = ''
  try {
    await artifactApi.remove(conversationId, turnId, artifactId)
    artifactStore.removeResultArtifact(artifactId)
    await loadActiveTurnFigureArtifacts()
    const remainingArtifactId = workspaceFigureArtifacts.value[0]?.artifact_id || null
    selectedArtifactId.value = remainingArtifactId
    if (!remainingArtifactId) {
      selectedFigurePayload.value = null
      artifactStore.setPlotlyFigure(null)
    }
  } catch (error: any) {
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
