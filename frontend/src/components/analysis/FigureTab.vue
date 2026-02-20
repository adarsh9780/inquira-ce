<template>
  <div class="flex flex-col h-full">
    <!-- Figure Header -->
    <div class="flex-shrink-0 bg-gray-50 border-b border-gray-200 px-4 py-3">
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-3">
          <h3 class="text-sm font-medium text-gray-900">Chart Visualization</h3>
          <span v-if="appStore.plotlyFigure || appStore.isCodeRunning" class="text-xs px-2 py-1 rounded"
                :class="appStore.isCodeRunning
                  ? 'text-orange-600 bg-orange-100'
                  : 'text-purple-600 bg-purple-100'">
            {{ appStore.isCodeRunning ? 'Processing' : 'Chart Ready' }}
          </span>
        </div>
        
        <div class="flex items-center space-x-2">
          <!-- Figure Selector -->
          <div v-if="orderedFigures && orderedFigures.length > 1" class="flex items-center space-x-2">
            <label for="figure-select" class="text-sm font-medium text-gray-700">Figure:</label>
            <select
              id="figure-select"
              v-model="selectedFigureIndex"
              class="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option
                v-for="(fig, index) in orderedFigures"
                :key="index"
                :value="index"
              >
                {{ fig.name }}
              </option>
            </select>
          </div>

          <!-- Download PNG Button -->
          <button
            @click="downloadPng"
            :disabled="!selectedFigure || isDownloading"
            class="inline-flex items-center px-3 py-2 border border-gray-300 text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
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
            class="inline-flex items-center px-3 py-2 border border-gray-300 text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
            :class="!selectedFigure ? 'opacity-50 cursor-not-allowed' : ''"
          >
            <DocumentIcon class="h-4 w-4 mr-1" />
            HTML
          </button>

          <!-- Fullscreen Button -->
          <button
            @click="toggleFullscreen"
            :disabled="!selectedFigure"
            class="inline-flex items-center px-3 py-2 border border-gray-300 text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
            :class="!selectedFigure ? 'opacity-50 cursor-not-allowed' : ''"
          >
            <ArrowsPointingOutIcon class="h-4 w-4 mr-1" />
            Fullscreen
          </button>
        </div>
      </div>
    </div>
    
    <!-- Plotly Chart Container -->
    <div class="flex-1 relative">
      <div
        v-if="selectedFigure"
        :key="selectedFigureIndex"
        ref="plotContainer"
        class="absolute inset-0 p-4"
      ></div>
      
      <!-- Empty State -->
      <div
        v-else
        class="absolute inset-0 flex items-center justify-center bg-gray-50"
      >
        <div class="text-center">
          <ChartBarIcon class="h-12 w-12 text-gray-300 mx-auto mb-3" />
          <p class="text-sm text-gray-500">No chart to display</p>
          <p class="text-xs text-gray-400 mt-1">Run code that generates a Plotly figure</p>
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
            <div :key="selectedFigureIndex" ref="fullscreenPlotContainer" class="absolute inset-0 p-4"></div>
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
import { 
  PhotoIcon, 
  DocumentIcon, 
  ArrowsPointingOutIcon, 
  ChartBarIcon,
  XMarkIcon 
} from '@heroicons/vue/24/outline'

const appStore = useAppStore()

const plotContainer = ref(null)
let ro = null
const fullscreenPlotContainer = ref(null)
const isDownloading = ref(false)
const isFullscreen = ref(false)
const selectedFigureIndex = ref(0)

const orderedFigures = computed(() => {
  if (!appStore.figures) return []
  return [...appStore.figures].slice().reverse()
})

const selectedFigure = computed(() => {
  if (!orderedFigures.value || orderedFigures.value.length === 0) return null
  const fig = orderedFigures.value[selectedFigureIndex.value]
  if (!fig || !fig.data) return null
  return fig.data
})

onMounted(async () => {
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
})

onUnmounted(() => {
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

// Watch for figures array changes to reset selection
watch(() => appStore.figures, (newFigures) => {
  if (newFigures && newFigures.length > 0) {
    selectedFigureIndex.value = 0
  }
})

// Re-render when the Figure tab becomes visible after being hidden by v-show
watch(() => appStore.activeTab, (tab) => {
  if (tab === 'figure' && selectedFigure.value) {
    nextTick(() => {
      renderPlot()
    })
  }
})

// The plot container will re-render automatically due to the :key attribute

async function waitForContainer(retries = 10) {
  while (retries-- > 0) {
    await nextTick()
    await new Promise(r => setTimeout(r, 50))
    const el = plotContainer.value
    if (el && el.clientWidth > 0 && el.clientHeight > 0) return true
  }
  return false
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

    const figureData = selectedFigure.value

    const layout = {
      ...figureData.layout,
      autosize: true,
      responsive: true,
      margin: { l: 50, r: 50, t: 50, b: 50 }
    }

    const config = {
      displayModeBar: true,
      displaylogo: false,
      modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d'],
      responsive: true
    }

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
    const figureData = selectedFigure.value
    
    const layout = {
      ...figureData.layout,
      autosize: true,
      responsive: true,
      margin: { l: 60, r: 60, t: 60, b: 60 }
    }
    
    const config = {
      displayModeBar: true,
      displaylogo: false,
      responsive: true
    }
    
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
    const filename = `chart_${new Date().toISOString().split('T')[0]}.png`

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
    const figureData = selectedFigure.value
    
    const htmlContent = `<!DOCTYPE html>
<html>
<head>
    <title>Chart Visualization</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"><\/script>
    <style>
        body { margin: 0; padding: 20px; font-family: Arial, sans-serif; }
        #chart { width: 100%; height: 600px; }
    </style>
</head>
<body>
    <h1>Chart Visualization</h1>
    <div id="chart"></div>
    <script>
        Plotly.newPlot('chart', ${JSON.stringify(figureData.data || [])}, ${JSON.stringify(figureData.layout || {})});
    <\/script>
</body>
</html>`
    
    const blob = new Blob([htmlContent], { type: 'text/html;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    
    link.setAttribute('href', url)
    link.setAttribute('download', `chart_${new Date().toISOString().split('T')[0]}.html`)
    link.style.visibility = 'hidden'
    
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    console.debug('HTML downloaded successfully')
    
  } catch (error) {
    console.error('Failed to download HTML:', error)
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
