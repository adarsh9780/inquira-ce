<template>
  <div class="h-full flex flex-col">
    <div class="flex items-center justify-between mb-3">
      <div class="flex items-center space-x-3 min-w-0">
        <button :class="tabBtn('data')" @click="activeTab = 'data'">Data</button>
        <button :class="tabBtn('schema')" @click="activeTab = 'schema'">Schema</button>
        <span v-if="tableName" class="ml-3 text-xs text-gray-500 truncate" :title="tableName">Table: {{ tableName }}</span>
      </div>
      <div class="flex items-center space-x-3">
        <select v-model="sampleType" @change="fetchDataPreview(true)" class="text-sm border border-gray-300 rounded px-2 py-1">
          <option value="random">Random</option>
          <option value="first">First 100</option>
        </select>
        <button @click="refreshCurrent" class="text-sm px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded border">Refresh</button>
        <button @click="clearCache" class="text-sm px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded border">Clear Cache</button>
        <button @click="exportSchema" class="text-sm px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded border">Export Schema</button>
      </div>
    </div>

    <div class="flex-1 min-h-0 overflow-hidden bg-white rounded-lg border">
      <!-- Data View with simple table -->
      <div v-if="activeTab === 'data'" class="h-full flex flex-col">
        <div v-if="isLoading" class="p-3 text-sm text-gray-500">Loading data...</div>
        <div v-else-if="error" class="p-3 text-sm text-red-600">{{ error }}</div>
        <div v-else class="h-full overflow-auto">
          <table class="min-w-full preview-table">
            <thead>
              <tr>
                <th
                  v-for="column in columns"
                  :key="`head-${column}`"
                  class="px-3 py-2 text-left text-xs font-medium text-gray-600 uppercase tracking-wider border-b bg-gray-50 sticky top-0 z-20 cursor-help"
                  :title="getColumnSchemaDescription(column) || 'No schema description'"
                >
                  {{ column }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, idx) in data" :key="idx" :class="idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'">
                <td
                  v-for="column in columns"
                  :key="`cell-${idx}-${column}`"
                  class="px-3 py-2 text-sm text-gray-900 border-b align-top"
                  :title="formatCellTitle(row[column])"
                >
                  <div class="truncate-120">{{ formatCell(row[column]) }}</div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Schema View -->
      <div v-else class="p-3">
        <div v-if="schemaLoading" class="text-sm text-gray-500">Loading schema...</div>
        <div v-else-if="schemaError" class="text-sm text-red-600">{{ schemaError }}</div>
        <div v-else>
          <div class="overflow-x-auto w-full">
            <table class="min-w-full divide-y divide-gray-200">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Column</th>
                  <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Description</th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
                <tr v-for="(col, i) in schema" :key="i">
                  <td class="px-3 py-2 text-sm text-gray-900">{{ col.name }}</td>
                  <td class="px-3 py-2 text-sm text-gray-700">{{ col.description || '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { previewService } from '../../services/previewService'
// toasts are lightweight; reuse window.alert for now (or wire your ToastContainer)

const activeTab = ref('data')
const tableName = ref('')
const sampleType = ref('random')
const data = ref([])
const columns = ref([])
const isLoading = ref(false)
const error = ref('')
const schema = ref([])
const schemaLoading = ref(false)
const schemaError = ref('')

function tabBtn(tab) {
  return [
    'px-3 py-1.5 rounded text-sm border',
    activeTab.value === tab ? 'bg-blue-100 text-blue-700 border-blue-200' : 'bg-gray-100 text-gray-700 hover:bg-gray-200 border-gray-200'
  ]
}

async function fetchDataPreview(forceRefresh = false) {
  if (isLoading.value) return
  isLoading.value = true
  error.value = ''
  data.value = []
  columns.value = []
  try {
    const response = await previewService.getDataPreview(sampleType.value, forceRefresh)
    if (response.success) {
      data.value = response.data
      if (data.value.length > 0) columns.value = Object.keys(data.value[0])
    } else {
      error.value = response.message || 'Failed to load data preview'
    }
  } catch (e) {
    error.value = 'Failed to load data preview'
  } finally {
    isLoading.value = false
  }
}

async function fetchSchemaData(forceRefresh = false) {
  if (schemaLoading.value) return
  schemaLoading.value = true
  schemaError.value = ''
  schema.value = []
  try {
    const settings = await previewService.getSettings(forceRefresh)
    if (!settings.data_path) {
      schemaError.value = 'Please configure your data file path in settings first.'
      return
    }
    try {
      const existingSchema = await previewService.loadSchema(settings.data_path, forceRefresh)
      if (existingSchema && existingSchema.columns) {
        schema.value = existingSchema.columns
      }
    } catch (_) {
      // ignore
    }
  } catch (e) {
    schemaError.value = 'Failed to load schema'
  } finally {
    schemaLoading.value = false
  }
}

function getColumnSchemaDescription(columnName) {
  const columnSchema = schema.value.find(col => col.name === columnName)
  return columnSchema?.description || null
}

function refreshCurrent() {
  if (activeTab.value === 'data') fetchDataPreview(true)
  else fetchSchemaData(true)
}

onMounted(() => {
  loadSettingsTableName().finally(() => {
    fetchDataPreview()
    fetchSchemaData()
  })
})

function clearCache() {
  try {
    previewService.clearPreviewCache()
    // replace with toast.success if available
    console.log('Preview cache cleared')
  } catch (e) {
    console.warn('Failed to clear cache')
  }
}

async function exportSchema() {
  try {
    // Try to get settings and then load schema
    const settings = await previewService.getSettings()
    if (!settings.data_path) return
    const existingSchema = await previewService.loadSchema(settings.data_path)
    if (!existingSchema || !existingSchema.columns) return
    const blob = new Blob([JSON.stringify(existingSchema, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'schema.json'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (e) {
    console.warn('Failed to export schema')
  }
}

async function loadSettingsTableName() {
  try {
    const settings = await previewService.getSettings()
    const backendName = settings?.table_name || settings?.data_table_name || settings?.table
    if (backendName) {
      tableName.value = backendName
      return
    }
    const path = settings?.data_path || ''
    if (path) {
      const base = String(path).split('/').pop() || ''
      tableName.value = base.split('.')[0] || ''
    }
  } catch (e) {
    tableName.value = ''
  }
}

// Table helpers
function formatCell(value) {
  if (value === null || value === undefined) return 'null'
  const s = String(value)
  return s.length > 120 ? s.slice(0, 120) + '…' : s
}

function formatCellTitle(value) {
  if (value === null || value === undefined) return 'null'
  return String(value)
}
</script>

<style scoped>
.preview-table {
  border-collapse: separate;
  border-spacing: 0;
}
.preview-table thead th {
  position: sticky;
  top: 0;
}
.truncate-120 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
