<template>
  <div class="h-full flex flex-col">
    <div class="flex items-center justify-between mb-3">
      <div class="text-sm text-gray-700">Schema Editor</div>
      <div class="flex items-center space-x-2">
        <button @click="refreshSchema" :disabled="schemaLoading" class="text-sm px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded border disabled:opacity-50">Refresh</button>
        <button @click="clearCache" class="text-sm px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded border">Clear Cache</button>
        <button @click="exportSchema" class="text-sm px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded border">Export</button>
        <button @click="saveSchema" :disabled="schemaLoading || !schemaEdited" class="text-sm px-3 py-1.5 bg-blue-600 text-white hover:bg-blue-700 rounded disabled:opacity-50">Save</button>
      </div>
    </div>
    <div class="flex-1 min-h-0 overflow-auto bg-white rounded-lg border p-3">
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
                <td class="px-3 py-2 text-sm text-gray-700">
                  <input type="text" class="w-full border rounded px-2 py-1 text-sm" :value="col.description" @input="e => updateSchemaDescription(i, e.target.value)" placeholder="Enter description for this column..." />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { previewService } from '../../services/previewService'
import { apiService } from '../../services/apiService'

const schema = ref([])
const schemaLoading = ref(false)
const schemaError = ref('')
const schemaEdited = ref(false)

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
    } catch (_) { /* ignore */ }
  } catch (e) {
    schemaError.value = 'Failed to load schema'
  } finally {
    schemaLoading.value = false
  }
}

function updateSchemaDescription(index, newDescription) {
  if (schema.value[index]) {
    schema.value[index].description = newDescription
    schemaEdited.value = true
  }
}

async function saveSchema() {
  try {
    const settings = await previewService.getSettings()
    if (!settings.data_path) {
      schemaError.value = 'Please configure your data file path in settings first.'
      return
    }
    await apiService.saveSchema(settings.data_path, null, schema.value)
    schemaEdited.value = false
    console.log('Schema saved')
  } catch (e) {
    schemaError.value = 'Failed to save schema'
  }
}

function refreshSchema() {
  fetchSchemaData(true)
}

onMounted(() => {
  fetchSchemaData()
})

function clearCache() {
  try {
    previewService.clearPreviewCache()
    console.log('Preview cache cleared')
  } catch (e) {
    console.warn('Failed to clear cache')
  }
}

async function exportSchema() {
  try {
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
</script>
