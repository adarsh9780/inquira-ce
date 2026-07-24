<template>
  <div ref="plotContainer" class="h-80 min-h-72 w-full" data-run-chart></div>
</template>

<script setup>
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import Plotly from 'plotly.js-cartesian-dist-min'
import { useAppCoordinatorStore } from '../../../stores/appCoordinatorStore'
import { normalizePlotlyFigure } from '../../../utils/figurePayload'
import { applyPlotlyConfigTheme, applyPlotlyTheme, PLOTLY_THEME_MODE } from '../../../utils/plotlyTheme'

const props = defineProps({
  output: { type: Object, required: true },
})

const appStore = useAppCoordinatorStore()
const plotContainer = ref(null)
let resizeObserver = null

async function renderPlot() {
  const rawFigure = normalizePlotlyFigure(props.output?.data ?? props.output)
  if (!rawFigure || !plotContainer.value) return
  await nextTick()
  const mode = String(appStore.plotlyThemeMode || '').toLowerCase() === PLOTLY_THEME_MODE.HARD
    ? PLOTLY_THEME_MODE.HARD
    : PLOTLY_THEME_MODE.SOFT
  const figure = applyPlotlyTheme(rawFigure, { mode, context: 'panel' }) || rawFigure
  const config = applyPlotlyConfigTheme({
    displayModeBar: true,
    displaylogo: false,
    modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d'],
    responsive: true,
  }, { mode })
  Plotly.purge(plotContainer.value)
  await Plotly.newPlot(
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
      try { Plotly.Plots.resize(plotContainer.value) } catch (_error) {}
    })
    resizeObserver.observe(plotContainer.value)
  }
})

watch(() => [props.output, appStore.uiTheme, appStore.plotlyThemeMode], () => void renderPlot(), { deep: true })

onUnmounted(() => {
  resizeObserver?.disconnect()
  if (plotContainer.value) Plotly.purge(plotContainer.value)
})
</script>
