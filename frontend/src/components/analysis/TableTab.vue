<template>
  <div class="flex flex-col h-full">
    <!-- Table Header -->
    <div class="flex-shrink-0 bg-gray-50 border-b border-gray-200 px-4 py-3">
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-3">
          <h3 class="text-sm font-medium text-gray-900">Data Table</h3>
          <span v-if="appStore.isCodeRunning" class="text-xs text-orange-600 bg-orange-100 px-2 py-1 rounded">
            Processing
          </span>
          <span v-else-if="rowCount > 0" class="text-xs text-blue-600 bg-blue-100 px-2 py-1 rounded">
            {{ rowCount.toLocaleString() }} rows
          </span>
        </div>
        
        <div class="flex items-center space-x-2">
          <!-- Dataframe Selector -->
          <div v-if="orderedDataframes && orderedDataframes.length > 1" class="flex items-center space-x-2">
            <label for="dataframe-select" class="text-sm font-medium text-gray-700">Dataframe:</label>
            <select
              id="dataframe-select"
              v-model="selectedDataframeIndex"
              class="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option
                v-for="(df, index) in orderedDataframes"
                :key="index"
                :value="index"
              >
                {{ df.name }}
              </option>
            </select>
          </div>

          <!-- Download CSV Button -->
          <button
            @click="downloadCsv"
            :disabled="!selectedDataframe || isDownloading"
            class="inline-flex items-center px-3 py-2 border border-gray-300 text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
            :class="!selectedDataframe ? 'opacity-50 cursor-not-allowed' : ''"
          >
            <ArrowDownTrayIcon v-if="!isDownloading" class="h-4 w-4 mr-1" />
            <div v-else class="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600 mr-1"></div>
            {{ isDownloading ? 'Downloading...' : 'Download CSV' }}
          </button>
        </div>
      </div>
    </div>
    
    <!-- AG Grid Container -->
    <div class="flex-1 relative">
      <ag-grid-vue
        v-if="selectedDataframe"
        :key="selectedDataframeIndex"
        class="ag-theme-quartz absolute inset-0"
        :columnDefs="columnDefs"
        :rowData="rowData"
        :defaultColDef="defaultColDef"
        :enableClipboard="true"
        :pagination="true"
        :paginationPageSize="100"
        :suppressMenuHide="true"
        :animateRows="true"
        :rowSelection="rowSelection"
        @grid-ready="onGridReady"
      ></ag-grid-vue>
      
      <!-- Empty State -->
      <div
        v-else
        class="absolute inset-0 flex items-center justify-center bg-gray-50"
      >
        <div class="text-center">
          <TableCellsIcon class="h-12 w-12 text-gray-300 mx-auto mb-3" />
          <p class="text-sm text-gray-500">No data to display</p>
          <p class="text-xs text-gray-400 mt-1">Run code to generate table data</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed, nextTick } from 'vue'
import { useAppStore } from '../../stores/appStore'
import apiService from '../../services/apiService'
import { AgGridVue } from 'ag-grid-vue3'
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community'
import 'ag-grid-community/styles/ag-theme-quartz.css'

// Register AG Grid Community modules
ModuleRegistry.registerModules([AllCommunityModule])
import {
  ArrowDownTrayIcon,
  TableCellsIcon
} from '@heroicons/vue/24/outline'


const appStore = useAppStore()

const isDownloading = ref(false)
const selectedDataframeIndex = ref(0)
let gridApi = null

const rowCount = computed(() => {
  return selectedDataframe.value ? selectedDataframe.value.length : 0
})

const orderedDataframes = computed(() => {
  if (!appStore.dataframes) return []
  // latest first
  return [...appStore.dataframes].slice().reverse()
})

const selectedDataframe = computed(() => {
  if (!orderedDataframes.value || orderedDataframes.value.length === 0) return null
  const df = orderedDataframes.value[selectedDataframeIndex.value]
  if (!df || !df.data) return null
  return df.data
})

const columnDefs = computed(() => {
  if (!selectedDataframe.value || selectedDataframe.value.length === 0) return []
  return generateColumnDefs(selectedDataframe.value)
})

const rowData = computed(() => {
  return selectedDataframe.value || []
})

const defaultColDef = {
  sortable: true,
  filter: true,
  resizable: true,
  minWidth: 120
}

const rowSelection = {
  mode: 'multiRow',
  enableClickSelection: true
}

onMounted(() => {
  // Data processing is now handled in the computed property
})

onUnmounted(() => {
  // Cleanup handled by Vue component
})

// Data processing is now handled in the computed property

// Watch for dataframes array changes to reset selection
watch(() => appStore.dataframes, (newDataframes) => {
  if (newDataframes && newDataframes.length > 0) {
    selectedDataframeIndex.value = 0
  }
})

// The grid should automatically update through Vue's reactive system
// when rowData computed property changes

function onGridReady(params) {
  gridApi = params.api
  // Grid is ready - no auto-sizing to avoid width issues
}

function generateColumnDefs(data) {
  if (!data || data.length === 0) return []

  const firstRow = data[0]
  const columns = Object.keys(firstRow).map(key => {
    const sampleValue = firstRow[key]

    return {
      headerName: key,
      field: key,
      cellRenderer: getCellRenderer(sampleValue),
      tooltipField: key,
      valueGetter: params => params.data?.[key],
      cellRendererParams: {
        truncate: 120
      },
      cellStyle: { whiteSpace: 'nowrap' }
    }
  })

  return columns
}

function getCellRenderer(value) {
  const truncateLen = 120
  if (typeof value === 'number') {
    return (params) => {
      const v = params.value
      if (v == null) return '<span class="text-gray-400 italic">null</span>'
      const s = typeof v === 'number' ? v.toLocaleString() : String(v)
      const display = s.length > truncateLen ? s.slice(0, truncateLen) + '…' : s
      const esc = (t) => String(t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
      return `<span title="${esc(s)}">${esc(display)}</span>`
    }
  }
  return (params) => {
    const v = params.value
    if (v == null) return '<span class="text-gray-400 italic">null</span>'
    const s = String(v)
    const display = s.length > truncateLen ? s.slice(0, truncateLen) + '…' : s
    const esc = (t) => String(t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    return `<span title="${esc(s)}">${esc(display)}</span>`
  }
}

async function downloadCsv() {
  if (!selectedDataframe.value || isDownloading.value) return

  isDownloading.value = true

  try {
    // Convert data to CSV format
    const csvContent = convertToCSV(selectedDataframe.value)

    // Get the selected dataframe name for the filename
    const dfName = appStore.dataframes[selectedDataframeIndex.value]?.name || 'dataframe'

    // Create and download file
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)

    link.setAttribute('href', url)
    link.setAttribute('download', `${dfName}_${new Date().toISOString().split('T')[0]}.csv`)
    link.style.visibility = 'hidden'

    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    console.debug('CSV downloaded successfully')

  } catch (error) {
    console.error('Failed to download CSV:', error)
  } finally {
    isDownloading.value = false
  }
}

function convertToCSV(data) {
  if (!data || data.length === 0) return ''
  
  const headers = Object.keys(data[0])
  const csvRows = []
  
  // Add headers
  csvRows.push(headers.map(header => `"${header}"`).join(','))
  
  // Add data rows
  for (const row of data) {
    const values = headers.map(header => {
      const value = row[header]
      if (value == null) return '""'
      return `"${String(value).replace(/"/g, '""')}"`
    })
    csvRows.push(values.join(','))
  }
  
  return csvRows.join('\n')
}

function processDataFrame(data) {
  // If data is already an array of objects, return as is
  if (Array.isArray(data) && data.length > 0 && typeof data[0] === 'object') {
    return data
  }

  // Handle pandas DataFrame format
  try {
    if (typeof data === 'object' && data !== null) {
      // Check if it's a pandas DataFrame with _mgr or _data attributes
      if (data._mgr && data._mgr.blocks) {
        // Extract data from pandas DataFrame blocks
        return extractDataFromDataFrame(data)
      }

      // Check if it has a 'data' property with array
      if (data.data && Array.isArray(data.data)) {
        return data.data
      }

      // Check if it has 'values' property
      if (data.values && Array.isArray(data.values)) {
        return data.values
      }

      // Check if it's a dict-like structure that can be converted
      if (data.columns && data.index && data.data) {
        return convertDictToArray(data)
      }
    }
  } catch (error) {
    console.warn('Failed to process DataFrame:', error)
  }

  // Return original data if conversion fails
  return data
}

function extractDataFromDataFrame(df) {
  try {
    // This is a simplified extraction - in practice, the backend should return JSON-serializable data
    if (df._mgr && df._mgr.blocks) {
      const blocks = df._mgr.blocks
      const columns = df.columns || []

      // Try to reconstruct data from blocks
      const result = []
      const numRows = blocks[0] ? blocks[0].values.length : 0

      for (let i = 0; i < numRows; i++) {
        const row = {}
        columns.forEach((col, colIndex) => {
          // This is a very simplified extraction
          row[col] = blocks[colIndex] ? blocks[colIndex].values[i] : null
        })
        result.push(row)
      }

      return result
    }
  } catch (error) {
    console.warn('Failed to extract DataFrame data:', error)
  }

  return []
}

function convertDictToArray(data) {
  try {
    const result = []
    const columns = data.columns || []
    const index = data.index || []
    const values = data.data || []

    // Convert to array of objects
    for (let i = 0; i < values.length; i++) {
      const row = {}
      columns.forEach((col, colIndex) => {
        row[col] = values[i][colIndex]
      })
      result.push(row)
    }

    return result
  } catch (error) {
    console.warn('Failed to convert dict to array:', error)
    return []
  }
}


</script>

<style>
/* AG Grid theme customizations */
.ag-theme-alpine {
  --ag-border-color: #e5e7eb;
  --ag-header-background-color: #f9fafb;
  --ag-odd-row-background-color: #ffffff;
  --ag-even-row-background-color: #f9fafb;
  --ag-row-hover-color: #f3f4f6;
  --ag-selected-row-background-color: #dbeafe;
}

.ag-theme-alpine .ag-header-cell-label {
  font-weight: 600;
}

.ag-theme-alpine .ag-cell {
  border-right: 1px solid var(--ag-border-color);
}
</style>
