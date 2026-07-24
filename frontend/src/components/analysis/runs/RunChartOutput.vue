<template>
  <div ref="plotContainer" class="plotly-surface h-80 min-h-72 w-full" data-run-chart></div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { usePreferencesStore } from '../../../stores/preferencesStore'
import { normalizePlotlyFigure } from '../../../utils/figurePayload'
import { loadPlotly } from '../../../utils/loadPlotly'
import { applyPlotlyConfigTheme, applyPlotlyTheme, PLOTLY_THEME_MODE } from '../../../utils/plotlyTheme'
import type { NormalizedPlotlyFigure } from '../../../utils/figurePayload'

const props = defineProps<{ output: Record<string, unknown> }>()

const preferencesStore = usePreferencesStore()
const plotContainer = ref<HTMLElement | null>(null)
let resizeObserver: ResizeObserver | null = null
let plotly: Awaited<ReturnType<typeof loadPlotly>> | null = null

async function renderPlot() {
  const rawFigure = normalizePlotlyFigure(props.output?.data ?? props.output)
  if (!rawFigure || !plotContainer.value) return
  plotly = await loadPlotly()
  await nextTick()
  const mode = PLOTLY_THEME_MODE.SOFT
  const figure = (applyPlotlyTheme(rawFigure, { mode, context: 'panel' }) || rawFigure) as NormalizedPlotlyFigure
  const config = applyPlotlyConfigTheme({
    displayModeBar: true,
    displaylogo: false,
    modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d'],
    responsive: true,
  }, { mode })
  plotly.purge(plotContainer.value)
  await plotly.newPlot(
    plotContainer.value,
    figure.data || [],
    { ...(figure.layout || {}), autosize: true },
    config,
  )
}

onMounted(() => {
  void renderPlot()
  if ('ResizeObserver' in window) {
    resizeObserver = new ResizeObserver(() => {
      try { plotly?.Plots.resize(plotContainer.value) } catch (_error) {}
    })
    if (plotContainer.value) resizeObserver.observe(plotContainer.value)
  }
})

watch(() => [props.output, preferencesStore.uiTheme], () => void renderPlot(), { deep: true })

onUnmounted(() => {
  resizeObserver?.disconnect()
  if (plotContainer.value) plotly?.purge(plotContainer.value)
})
</script>
