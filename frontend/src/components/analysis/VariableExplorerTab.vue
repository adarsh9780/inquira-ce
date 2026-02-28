<template>
  <div class="flex h-full flex-col overflow-hidden rounded-lg border border-gray-200 bg-white">
    <div class="border-b border-gray-200 bg-gray-50 px-4 py-3">
      <h3 class="text-sm font-semibold text-gray-900">Variable Explorer</h3>
      <p class="mt-1 text-xs text-gray-600">Inspect scalars and execution artifacts from the latest run.</p>
    </div>

    <div class="min-h-0 flex-1 overflow-y-auto p-4">
      <div v-if="!hasVariables" class="flex h-full items-center justify-center text-center text-gray-500">
        <div>
          <p class="text-sm">No variables available</p>
          <p class="mt-1 text-xs text-gray-400">Run code to populate variable explorer.</p>
        </div>
      </div>

      <div v-else class="space-y-4">
        <section>
          <h4 class="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">Scalars ({{ appStore.scalars.length }})</h4>
          <div class="space-y-2">
            <div
              v-for="(scalar, idx) in appStore.scalars"
              :key="`scalar-${idx}-${scalar.name}`"
              class="rounded border border-gray-200 bg-white p-3"
            >
              <div class="text-xs font-semibold text-gray-700">{{ scalar.name }}</div>
              <pre class="mt-1 whitespace-pre-wrap break-words text-xs text-gray-900">{{ formatScalar(scalar.value) }}</pre>
            </div>
          </div>
        </section>

        <section>
          <h4 class="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">Dataframes ({{ appStore.dataframes.length }})</h4>
          <div class="space-y-2">
            <div
              v-for="(df, idx) in appStore.dataframes"
              :key="`df-${idx}-${df.name}`"
              class="rounded border border-gray-200 bg-white p-3 text-xs text-gray-700"
            >
              <div class="font-semibold text-gray-800">{{ df.name }}</div>
              <div class="mt-1 grid grid-cols-2 gap-2">
                <div>rows: {{ getRowCount(df.data) }}</div>
                <div>artifact: {{ df.data?.artifact_id || 'inline' }}</div>
              </div>
            </div>
          </div>
        </section>

        <section>
          <h4 class="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">Figures ({{ appStore.figures.length }})</h4>
          <div class="space-y-2">
            <div
              v-for="(fig, idx) in appStore.figures"
              :key="`fig-${idx}-${fig.name}`"
              class="rounded border border-gray-200 bg-white p-3 text-xs text-gray-700"
            >
              <div class="font-semibold text-gray-800">{{ fig.name }}</div>
              <div class="mt-1">traces: {{ Array.isArray(fig.data?.data) ? fig.data.data.length : 0 }}</div>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useAppStore } from '../../stores/appStore'

const appStore = useAppStore()

const hasVariables = computed(() => (
  (appStore.scalars?.length || 0) > 0 ||
  (appStore.dataframes?.length || 0) > 0 ||
  (appStore.figures?.length || 0) > 0
))

function formatScalar(value) {
  if (typeof value === 'string') return value
  try {
    return JSON.stringify(value, null, 2)
  } catch (_error) {
    return String(value)
  }
}

function getRowCount(data) {
  if (typeof data?.row_count === 'number') return data.row_count
  if (Array.isArray(data?.data)) return data.data.length
  if (Array.isArray(data)) return data.length
  return 0
}
</script>
