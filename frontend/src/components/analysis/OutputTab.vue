<template>
  <div class="flex h-full flex-col overflow-hidden rounded-lg border" style="background-color: var(--color-base); border-color: var(--color-border);">
    <Teleport to="#workspace-right-pane-toolbar" v-if="isMounted && appStore.dataPane === 'output'">
      <div class="flex items-center justify-end w-full">
        <p class="text-xs hidden sm:block" style="color: var(--color-text-muted);">Review stdout, stderr, warnings, and tracebacks from recent runs</p>
      </div>
    </Teleport>

    <div class="border-b px-4 py-2.5" style="border-color: var(--color-border); background-color: var(--color-surface);">
      <div class="flex items-center justify-between gap-3">
        <div class="inline-flex items-center rounded-xl p-0.5" style="background-color: color-mix(in srgb, var(--color-border) 35%, transparent);">
          <button
            v-for="option in filterOptions"
            :key="option.value"
            @click="activeFilter = option.value"
            class="rounded-lg px-2.5 py-1 text-xs transition-colors"
            :class="activeFilter === option.value ? 'bg-white shadow-sm' : ''"
            :style="activeFilter === option.value ? 'color: var(--color-text-main);' : 'color: var(--color-text-muted);'"
          >
            {{ option.label }}
          </button>
        </div>
        <div class="text-xs tabular-nums" style="color: var(--color-text-muted);">
          {{ filteredEntries.length }} {{ filteredEntries.length === 1 ? 'run' : 'runs' }}
        </div>
      </div>
    </div>

    <div class="min-h-0 flex-1 overflow-y-auto">
      <div v-if="filteredEntries.length === 0" class="flex h-full items-center justify-center text-center" style="color: var(--color-text-muted);">
        <div>
          <p class="text-sm">No output yet</p>
          <p class="mt-1 text-xs">Run Python code to see print output and errors here.</p>
        </div>
      </div>

      <div v-else class="divide-y" style="border-color: color-mix(in srgb, var(--color-border) 80%, transparent);">
        <article
          v-for="(entry, idx) in filteredEntries"
          :key="entry.createdAt || idx"
          class="px-4 py-3"
        >
          <div class="mb-2 flex items-center justify-between text-[11px] uppercase tracking-wide" style="color: var(--color-text-muted);">
            <span>{{ entry.label || 'Python output' }}</span>
            <span>{{ formatTimestamp(entry.createdAt) }}</span>
          </div>

          <pre
            v-if="showStdout(entry)"
            class="whitespace-pre-wrap break-words rounded-md px-3 py-2 text-xs font-mono leading-5"
            style="color: var(--color-text-main); background-color: color-mix(in srgb, var(--color-surface) 70%, transparent);"
          >{{ entry.stdout }}</pre>
          <pre
            v-if="showStderr(entry)"
            class="mt-2 whitespace-pre-wrap break-words rounded-r-md border-l-2 bg-red-50/55 px-3 py-2 text-xs font-mono leading-5 text-red-700"
            style="border-left-color: color-mix(in srgb, #ef4444 75%, var(--color-border));"
          >{{ entry.stderr }}</pre>
        </article>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useAppStore } from '../../stores/appStore'

const appStore = useAppStore()
const isMounted = ref(false)
const activeFilter = ref('all')

const filterOptions = [
  { value: 'all', label: 'All' },
  { value: 'stdout', label: 'stdout' },
  { value: 'stderr', label: 'stderr' },
]

onMounted(() => {
  isMounted.value = true
})

const analysisEntries = computed(() => {
  const entries = Array.isArray(appStore.terminalEntries) ? appStore.terminalEntries : []
  return entries
    .filter((entry) => entry?.kind === 'output' && entry?.source === 'analysis')
    .slice()
    .reverse()
})

const filteredEntries = computed(() => {
  if (activeFilter.value === 'stdout') {
    return analysisEntries.value.filter((entry) => Boolean(String(entry?.stdout || '').trim()))
  }
  if (activeFilter.value === 'stderr') {
    return analysisEntries.value.filter((entry) => Boolean(String(entry?.stderr || '').trim()))
  }
  return analysisEntries.value
})

function showStdout(entry) {
  if (activeFilter.value === 'stderr') return false
  return Boolean(String(entry?.stdout || '').trim())
}

function showStderr(entry) {
  if (activeFilter.value === 'stdout') return false
  return Boolean(String(entry?.stderr || '').trim())
}

function formatTimestamp(value) {
  const raw = String(value || '').trim()
  if (!raw) return 'n/a'
  const date = new Date(raw)
  if (Number.isNaN(date.getTime())) return 'n/a'
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
</script>
