<template>
  <div ref="plotContainer" class="plotly-surface h-80 min-h-72 w-full" data-run-chart></div>
</template>

<script setup>
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { usePreferencesStore } from '../../../stores/preferencesStore'
import { normalizePlotlyFigure } from '../../../utils/figurePayload'
import { loadPlotly } from '../../../utils/loadPlotly'
import { applyPlotlyConfigTheme, applyPlotlyTheme, PLOTLY_THEME_MODE } from '../../../utils/plotlyTheme'

const props = defineProps({
  output: { type: Object, required: true },
})

const preferencesStore = usePreferencesStore()
const plotContainer = ref(null)
let resizeObserver = null
let plotly = null

async function renderPlot() {
  const rawFigure = normalizePlotlyFigure(props.output?.data ?? props.output)
  if (!rawFigure || !plotContainer.value) return
  plotly = await loadPlotly()
  await nextTick()
  const mode = PLOTLY_THEME_MODE.SOFT
  const figure = applyPlotlyTheme(rawFigure, { mode, context: 'panel' }) || rawFigure
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
    resizeObserver.observe(plotContainer.value)
  }
})

watch(() => [props.output, preferencesStore.uiTheme], () => void renderPlot(), { deep: true })

onUnmounted(() => {
  resizeObserver?.disconnect()
  if (plotContainer.value) plotly?.purge(plotContainer.value)
})
</script>
