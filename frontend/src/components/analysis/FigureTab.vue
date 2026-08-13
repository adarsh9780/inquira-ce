<template>
  <div class="flex flex-col h-full">
    <Teleport to="#workspace-right-pane-toolbar-center" v-if="isMounted && uiStore.dataPane === 'figure'">
      <div
        v-if="figureDropdownOptions.length > 0"
        class="flex min-w-0 max-w-full items-center"
        :class="toolbarMode === 'wide' ? 'w-[19rem]' : toolbarMode === 'compact' ? 'w-48' : 'w-36'"
      >
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
        <div v-if="toolbarMode === 'wide'" class="flex min-w-0 items-center space-x-3 text-sm">
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
            type="button"
            :disabled="!activeChartSpec || isLoadingChartContext"
            class="btn-icon h-8 w-8 shrink-0 border"
            style="border-color: var(--color-border); color: var(--color-text-muted);"
            :class="(!activeChartSpec || isLoadingChartContext) ? 'opacity-50 cursor-not-allowed' : editorOpen ? 'is-active' : ''"
            :title="editorOpen ? 'Close chart editor' : 'Edit chart data and spec'"
            :aria-label="editorOpen ? 'Close chart editor' : 'Edit chart data and spec'"
            :aria-pressed="editorOpen"
            @click="editorOpen = !editorOpen"
          >
            <PencilSquareIcon class="h-4 w-4" />
          </button>
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

    <div
      class="chart-workspace min-h-0 flex-1 mt-1"
      :class="editorOpen && activeChartSpec ? 'is-editing' : ''"
      :data-toolbar-mode="toolbarMode"
    >
      <section class="chart-canvas relative min-h-0" aria-label="Chart preview">
        <div
          v-if="selectedFigure"
          :key="selectedArtifactId"
          ref="plotContainer"
          class="plotly-surface absolute inset-0 p-4"
        ></div>

        <div v-else class="absolute inset-0" style="background-color: var(--color-base);">
          <AppEmptyState
            :title="artifactListError ? 'Charts unavailable' : unavailableArtifactCount > 0 ? 'Saved charts unavailable' : 'No saved charts'"
            :description="artifactListError || (unavailableArtifactCount > 0 ? artifactUnavailableDescription('chart', unavailableArtifactCount) : 'Ask AI for a chart, or promote one from Runs.')"
          ><template #icon><ChartBarIcon class="h-7 w-7" /></template></AppEmptyState>
        </div>
      </section>

      <aside
        v-if="editorOpen && activeChartSpec"
        class="chart-inspector min-h-0 overflow-hidden"
        aria-label="Chart editor"
      >
        <header class="inspector-header flex items-start justify-between gap-3">
          <div class="min-w-0">
            <p class="inspector-eyebrow">Chart editor</p>
            <h2 class="truncate text-sm font-semibold" style="color: var(--color-text-main);">
              {{ activeChartSpec.title }}
            </h2>
            <p class="mt-1 truncate text-xs" style="color: var(--color-text-muted);">
              {{ sourceLogicalName }}
            </p>
          </div>
          <button type="button" class="btn-icon h-7 w-7 shrink-0" aria-label="Close chart editor" @click="editorOpen = false">
            <XMarkIcon class="h-4 w-4" />
          </button>
        </header>

        <div class="inspector-tabs" role="tablist" aria-label="Chart editor sections">
          <button type="button" role="tab" :aria-selected="editorTab === 'data'" :class="editorTab === 'data' ? 'is-active' : ''" @click="editorTab = 'data'">
            <CircleStackIcon class="h-4 w-4" /> Data
          </button>
          <button type="button" role="tab" :aria-selected="editorTab === 'spec'" :class="editorTab === 'spec' ? 'is-active' : ''" @click="editorTab = 'spec'">
            <CodeBracketIcon class="h-4 w-4" /> Spec
          </button>
        </div>

        <div v-if="editorTab === 'data'" class="inspector-body overflow-auto">
          <div class="data-summary">
            <span>{{ sourceRowCountLabel }}</span>
            <span aria-hidden="true">·</span>
            <span>{{ sourceColumns.length }} columns</span>
          </div>
          <p class="mt-4 text-xs font-semibold uppercase tracking-[0.08em]" style="color: var(--color-text-muted);">Fields used</p>
          <dl class="field-list mt-2">
            <div v-for="fieldItem in encodedFields" :key="fieldItem.channel">
              <dt>{{ fieldItem.channel }}</dt>
              <dd>{{ fieldItem.field }}</dd>
            </div>
          </dl>
          <p v-if="chartContextError" class="inline-error mt-4" role="alert">{{ chartContextError }}</p>
          <button type="button" class="inspector-secondary mt-5" :disabled="!sourceArtifactId" @click="openSourceTable">
            Open source table
          </button>
        </div>

        <div v-else class="inspector-body spec-editor min-h-0">
          <label for="chart-spec-json" class="sr-only">Chart JSON spec</label>
          <textarea
            id="chart-spec-json"
            v-model="specDraft"
            spellcheck="false"
            aria-describedby="chart-spec-help chart-spec-error"
          ></textarea>
          <p id="chart-spec-help" class="mt-2 text-xs leading-5" style="color: var(--color-text-muted);">
            Edit mark, fields, labels, and chart options. Inquira validates this spec before rendering.
          </p>
          <p v-if="specError" id="chart-spec-error" class="inline-error mt-3" role="alert">{{ specError }}</p>
          <div class="mt-4 flex items-center justify-end gap-2">
            <button type="button" class="inspector-secondary" @click="resetSpecDraft">Reset</button>
            <button type="button" class="inspector-primary" :disabled="!sourceRows.length" @click="applySpecRevision">Apply revision</button>
          </div>
        </div>
      </aside>
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
import { compileChartSpec, parseChartSpec, type ChartSpec } from '../../utils/chartSpec'
import { loadPlotly } from '../../utils/loadPlotly'
import { persistExportFile } from '../../utils/exportFile'
import {
  artifactUnavailableDescription,
  isArtifactAvailable,
  isArtifactPayloadMissingError,
} from '../../utils/artifactAvailability'
import { applyPlotlyTheme, applyPlotlyConfigTheme, PLOTLY_THEME_MODE } from '../../utils/plotlyTheme'
import { toast } from '../../composables/useToast'
import {
  ArrowDownTrayIcon,
  ChartBarIcon,
  CircleStackIcon,
  CodeBracketIcon,
  PencilSquareIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'

const props = withDefaults(defineProps<{
  toolbarMode?: 'wide' | 'compact' | 'minimal'
}>(), {
  toolbarMode: 'wide',
})
const toolbarMode = computed(() => props.toolbarMode)
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
const workspaceChartSpecArtifacts = ref<any[]>([])
const workspaceDataframeArtifacts = ref<any[]>([])
const selectedFigurePayload = ref<any>(null)
const activeChartSpec = ref<ChartSpec | null>(null)
const originalChartSpec = ref<ChartSpec | null>(null)
const sourceRows = ref<Record<string, any>[]>([])
const sourceColumns = ref<string[]>([])
const sourceRowCount = ref(0)
const sourceArtifactId = ref('')
const editorOpen = ref(false)
const editorTab = ref<'data' | 'spec'>('data')
const specDraft = ref('')
const specError = ref('')
const chartContextError = ref('')
const isLoadingChartContext = ref(false)
const artifactListError = ref('')
const exportMenuOpen = ref(false)
const exportMenuButtonRef = ref<any>(null)
const exportMenuPosition = ref({ x: 0, y: 0 })
let listAbortController: AbortController | null = null
let figureAbortController: AbortController | null = null
let chartContextAbortController: AbortController | null = null
let plotly: any = null

const exportMenuItems = computed(() => [
  { id: 'png', label: 'PNG image (.png)' },
  { id: 'html', label: 'HTML file (.html)' },
  { id: 'delete', label: 'Delete chart', dividerBefore: true, destructive: true, disabled: !canDeleteSelectedFigure.value || isDeletingArtifact.value },
])

const allPersistedFigureArtifacts = computed(() => (
  Array.isArray(workspaceFigureArtifacts.value) ? workspaceFigureArtifacts.value : []
))
const persistedFigureArtifacts = computed(() => allPersistedFigureArtifacts.value.filter(isArtifactAvailable))
const unavailableArtifactCount = computed(() => (
  allPersistedFigureArtifacts.value.filter((artifact) => !isArtifactAvailable(artifact)).length
))

const liveFigureArtifacts = computed(() => {
  const persistedIds = new Set(
    allPersistedFigureArtifacts.value
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
const sourceLogicalName = computed(() => String(activeChartSpec.value?.data?.logical_name || '').trim())
const sourceRowCountLabel = computed(() => `${Number(sourceRowCount.value || sourceRows.value.length).toLocaleString()} rows`)
const encodedFields = computed(() => Object.entries(activeChartSpec.value?.encoding || {})
  .filter((entry): entry is [string, any] => Boolean(entry[1]?.field))
  .map(([channel, encoding]) => ({ channel, field: String(encoding.field) })))

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
  chartContextAbortController?.abort()
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
  workspaceChartSpecArtifacts.value = []
  workspaceDataframeArtifacts.value = []
  clearChartContext()
  editorOpen.value = false
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
  void loadSelectedChartContext(artifactId)
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
    const [response, specResponse, dataframeResponse]: any[] = await Promise.all([
      artifactApi.listTurn(conversationId, turnId, 'figure', { signal: listAbortController.signal }),
      artifactApi.listTurn(conversationId, turnId, 'chart_spec', { signal: listAbortController.signal }),
      artifactApi.listTurn(conversationId, turnId, 'dataframe', { signal: listAbortController.signal }),
    ])
    const artifacts = Array.isArray(response?.artifacts) ? response.artifacts : []
    workspaceFigureArtifacts.value = artifacts
    workspaceChartSpecArtifacts.value = Array.isArray(specResponse?.artifacts) ? specResponse.artifacts : []
    workspaceDataframeArtifacts.value = Array.isArray(dataframeResponse?.artifacts) ? dataframeResponse.artifacts : []
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
    if (nextSelection === selectedArtifactId.value) {
      await loadSelectedChartContext(nextSelection)
    }
  } catch (error: any) {
    if (error?.name === 'AbortError') return
    console.warn('Failed to load active turn figure artifacts:', error)
    artifactListError.value = 'Saved charts could not be loaded. Try refreshing the workspace.'
    workspaceFigureArtifacts.value = []
    workspaceChartSpecArtifacts.value = []
    workspaceDataframeArtifacts.value = []
    clearChartContext()
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
    if (isArtifactPayloadMissingError(error)) {
      workspaceFigureArtifacts.value = workspaceFigureArtifacts.value.map((artifact) => (
        String(artifact?.artifact_id || '').trim() === normalizedArtifactId
          ? { ...artifact, status: 'missing' }
          : artifact
      ))
      artifactStore.removeResultArtifact(normalizedArtifactId)
      selectedArtifactId.value = null
      selectedFigurePayload.value = null
      artifactStore.setPlotlyFigure(null)
      artifactListError.value = ''
      return
    }
    selectedFigurePayload.value = null
    artifactStore.setPlotlyFigure(null)
    artifactListError.value = 'We could not read this saved chart. Try again, or run the question again to recreate it.'
  } finally {
    isLoadingFigure.value = false
  }
}

function clearChartContext() {
  activeChartSpec.value = null
  originalChartSpec.value = null
  sourceRows.value = []
  sourceColumns.value = []
  sourceRowCount.value = 0
  sourceArtifactId.value = ''
  specDraft.value = ''
  specError.value = ''
  chartContextError.value = ''
}

function figureSourceLogicalName(figure: any) {
  const explicit = String(figure?.chart_spec?.data?.logical_name || '').trim()
  if (explicit) return explicit
  const logicalName = String(figure?.logical_name || '').trim()
  return logicalName.endsWith('_chart') ? logicalName.slice(0, -'_chart'.length) : ''
}

function chartSpecSummaryForFigure(figure: any) {
  const sourceName = figureSourceLogicalName(figure)
  const expectedName = sourceName ? `${sourceName}_chart_spec` : ''
  return workspaceChartSpecArtifacts.value.find((artifact) => (
    expectedName && String(artifact?.logical_name || '').trim() === expectedName
  )) || (workspaceChartSpecArtifacts.value.length === 1 ? workspaceChartSpecArtifacts.value[0] : null)
}

function dataframeSummaryForSpec(spec: ChartSpec) {
  const explicitId = String(spec.data.artifact_id || '').trim()
  return workspaceDataframeArtifacts.value.find((artifact) => (
    (explicitId && String(artifact?.artifact_id || '').trim() === explicitId)
    || String(artifact?.logical_name || '').trim() === spec.data.logical_name
  )) || null
}

async function loadSelectedChartContext(artifactId: any) {
  const normalizedArtifactId = String(artifactId || '').trim()
  const conversationId = String(conversationStore.activeConversationId || '').trim()
  const turnId = String(conversationStore.activeTurnId || '').trim()
  if (!normalizedArtifactId) {
    clearChartContext()
    return
  }

  chartContextAbortController?.abort()
  chartContextAbortController = new AbortController()
  const signal = chartContextAbortController.signal
  isLoadingChartContext.value = true
  chartContextError.value = ''
  specError.value = ''
  try {
    const figure = orderedFigures.value.find((item) => String(item?.artifact_id || '').trim() === normalizedArtifactId)
    if (!figure) {
      clearChartContext()
      return
    }
    let rawSpec = figure?.chart_spec || figure?.data?.chart_spec || null
    if (!rawSpec && conversationId && turnId) {
      const specSummary = chartSpecSummaryForFigure(figure)
      if (!specSummary?.artifact_id) {
        clearChartContext()
        return
      }
      const metadata: any = await artifactApi.metadata(
        conversationId,
        turnId,
        specSummary.artifact_id,
        { signal },
      )
      rawSpec = metadata?.payload?.chart_spec ?? metadata?.payload?.value ?? metadata?.payload
    }
    const spec = parseChartSpec(rawSpec)
    const dataframe = dataframeSummaryForSpec(spec)
    if (!dataframe?.artifact_id || !conversationId || !turnId) {
      activeChartSpec.value = spec
      originalChartSpec.value = spec
      specDraft.value = JSON.stringify(spec, null, 2)
      sourceArtifactId.value = ''
      chartContextError.value = 'The source table for this chart is no longer available.'
      return
    }
    const rowsPayload: any = await artifactApi.turnRows(
      conversationId,
      turnId,
      dataframe.artifact_id,
      0,
      5000,
      { signal },
    )
    if (normalizedArtifactId !== String(selectedArtifactId.value || '').trim()) return
    const rows = Array.isArray(rowsPayload?.rows) ? rowsPayload.rows : []
    activeChartSpec.value = spec
    originalChartSpec.value = spec
    specDraft.value = JSON.stringify(spec, null, 2)
    sourceRows.value = rows
    sourceColumns.value = Array.isArray(rowsPayload?.columns)
      ? rowsPayload.columns.map((column: any) => String(column))
      : (rows[0] ? Object.keys(rows[0]) : [])
    sourceRowCount.value = Number(rowsPayload?.row_count ?? rows.length)
    sourceArtifactId.value = String(dataframe.artifact_id)
  } catch (error: any) {
    if (error?.name === 'AbortError') return
    console.warn('Failed to load chart editing context:', error)
    clearChartContext()
    chartContextError.value = 'The chart is available, but its editable spec or source data could not be loaded.'
  } finally {
    isLoadingChartContext.value = false
  }
}

function resetSpecDraft() {
  specDraft.value = originalChartSpec.value ? JSON.stringify(originalChartSpec.value, null, 2) : ''
  specError.value = ''
}

function applySpecRevision() {
  specError.value = ''
  try {
    const parsed = parseChartSpec(JSON.parse(specDraft.value))
    const figure = compileChartSpec(parsed, sourceRows.value)
    const revisionId = artifactPresentation.promoteUserRunFigure({
      data: figure,
      logical_name: `${parsed.data.logical_name}_chart_revision`,
      display_name: parsed.title,
      chart_spec: parsed,
      source_artifact_id: sourceArtifactId.value,
    }, {
      runId: `chart-editor-${conversationStore.activeTurnId || 'turn'}`,
      outputId: Date.now().toString(36),
    })
    if (!revisionId) throw new Error('The chart revision could not be created.')
    activeChartSpec.value = parsed
    originalChartSpec.value = parsed
    specDraft.value = JSON.stringify(parsed, null, 2)
    selectedArtifactId.value = revisionId
    toast.success('Chart updated', 'A user revision is now shown in the chart canvas.')
  } catch (error: any) {
    specError.value = error instanceof SyntaxError
      ? 'The spec is not valid JSON.'
      : String(error?.message || 'The chart spec could not be applied.')
  }
}

function openSourceTable() {
  const workspaceId = String(workspaceStore.activeWorkspaceId || '').trim()
  const artifactId = String(sourceArtifactId.value || '').trim()
  if (!workspaceId || !artifactId) return
  artifactStore.setSelectedTableArtifact(workspaceId, artifactId, conversationStore.activeTurnId)
  uiStore.setDataPane('table')
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
    const themeMode = PLOTLY_THEME_MODE.HARD
    const figureData = applyPlotlyTheme(rawFigureData, { mode: themeMode, context: 'panel' }) || rawFigureData

    const layout = {
      ...(figureData.layout || {}),
      autosize: true,
      responsive: true,
    }

    const config = applyPlotlyConfigTheme(
      {
        displayModeBar: 'hover',
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
    const themeMode = PLOTLY_THEME_MODE.HARD
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
            font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: white;
            color: CanvasText;
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
.chart-workspace {
  display: grid;
  height: 100%;
  overflow: hidden;
  background: var(--color-base);
}

.chart-workspace.is-editing {
  grid-template-columns: minmax(0, 1fr) minmax(19rem, 22rem);
  gap: 0.75rem;
}

.chart-canvas {
  min-width: 0;
  border: 1px solid transparent;
  border-radius: 0.75rem;
  overflow: hidden;
  background: var(--color-base);
}

.chart-workspace.is-editing .chart-canvas {
  border-color: var(--color-border);
}

.chart-inspector {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--color-border);
  border-radius: 0.75rem;
  background: var(--color-panel-elevated);
  box-shadow: var(--shadow-lifted);
}

.inspector-header {
  padding: 1rem;
  border-bottom: 1px solid var(--color-border);
}

.inspector-eyebrow {
  margin-bottom: 0.25rem;
  color: var(--color-text-muted);
  font-size: 0.6875rem;
  font-weight: 650;
  letter-spacing: 0.09em;
  line-height: 1rem;
  text-transform: uppercase;
}

.inspector-tabs {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.25rem;
  margin: 0.75rem 1rem 0;
  padding: 0.25rem;
  border-radius: 0.625rem;
  background: var(--color-panel-muted);
}

.inspector-tabs button {
  display: inline-flex;
  min-height: 2rem;
  align-items: center;
  justify-content: center;
  gap: 0.375rem;
  border-radius: 0.4375rem;
  color: var(--color-text-muted);
  font-size: 0.75rem;
  font-weight: 600;
}

.inspector-tabs button.is-active {
  color: var(--color-text-main);
  background: var(--color-panel-elevated);
  box-shadow: var(--shadow-button);
}

.inspector-body {
  min-height: 0;
  flex: 1;
  padding: 1rem;
}

.data-summary {
  display: flex;
  gap: 0.5rem;
  color: var(--color-text-muted);
  font-size: 0.75rem;
  line-height: 1.25rem;
}

.field-list {
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: 0.625rem;
}

.field-list > div {
  display: grid;
  grid-template-columns: 4.5rem minmax(0, 1fr);
  gap: 0.75rem;
  padding: 0.625rem 0.75rem;
  border-bottom: 1px solid var(--color-border);
  font-size: 0.75rem;
  line-height: 1.25rem;
}

.field-list > div:last-child { border-bottom: 0; }
.field-list dt { color: var(--color-text-muted); text-transform: uppercase; }
.field-list dd { overflow: hidden; color: var(--color-text-main); font-family: var(--font-mono); text-overflow: ellipsis; white-space: nowrap; }

.spec-editor {
  display: flex;
  flex-direction: column;
}

.spec-editor textarea {
  width: 100%;
  min-height: 12rem;
  flex: 1;
  resize: none;
  border: 1px solid var(--color-border);
  border-radius: 0.625rem;
  padding: 0.75rem;
  outline: none;
  background: var(--color-panel-muted);
  color: var(--color-text-main);
  font-family: var(--font-mono);
  font-size: 0.75rem;
  line-height: 1.35rem;
  tab-size: 2;
}

.spec-editor textarea:focus {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 0.1875rem color-mix(in srgb, var(--color-accent) 16%, transparent);
}

.inline-error {
  padding: 0.625rem 0.75rem;
  border: 1px solid color-mix(in srgb, var(--color-danger) 35%, var(--color-border));
  border-radius: 0.5rem;
  background: color-mix(in srgb, var(--color-danger) 8%, var(--color-panel-elevated));
  color: var(--color-danger);
  font-size: 0.75rem;
  line-height: 1.25rem;
}

.inspector-primary,
.inspector-secondary {
  min-height: 2rem;
  border-radius: 0.5rem;
  padding: 0.4375rem 0.75rem;
  font-size: 0.75rem;
  font-weight: 650;
}

.inspector-primary {
  background: var(--color-text-main);
  color: var(--color-base);
}

.inspector-secondary {
  border: 1px solid var(--color-border);
  background: var(--color-panel-elevated);
  color: var(--color-text-main);
}

.inspector-primary:disabled,
.inspector-secondary:disabled { cursor: not-allowed; opacity: 0.45; }

.btn-icon.is-active {
  border-color: color-mix(in srgb, var(--color-accent) 35%, var(--color-border));
  background: color-mix(in srgb, var(--color-accent) 10%, var(--color-panel-elevated));
  color: var(--color-accent);
}

.chart-workspace.is-editing[data-toolbar-mode='compact'],
.chart-workspace.is-editing[data-toolbar-mode='minimal'] {
  grid-template-columns: minmax(0, 1fr);
  grid-template-rows: minmax(14rem, 1fr) minmax(16rem, 0.9fr);
}

.chart-workspace[data-toolbar-mode='compact'] .chart-inspector,
.chart-workspace[data-toolbar-mode='minimal'] .chart-inspector {
  box-shadow: var(--shadow-lifted);
}
</style>
