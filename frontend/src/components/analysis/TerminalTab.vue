<template>
  <div class="flex h-full flex-col overflow-hidden rounded-lg border border-gray-200 bg-white">
    <div class="flex items-center justify-between border-b border-gray-200 bg-gray-50 px-4 py-3">
      <div class="flex items-center space-x-2">
        <CommandLineIcon class="h-5 w-5 text-gray-700" />
        <h3 class="text-sm font-semibold text-gray-900">Terminal</h3>
        <span class="rounded bg-gray-200 px-2 py-0.5 text-xs text-gray-700">{{ shellLabel }}</span>
      </div>
      <div class="text-xs text-gray-600">cwd: {{ displayCwd }}</div>
    </div>

    <div v-if="!appStore.terminalConsentGranted" class="flex-1 p-5">
      <div class="mx-auto max-w-xl rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        <p class="font-semibold">Local terminal access</p>
        <p class="mt-2">Commands here run on your machine with your user permissions in the active workspace context.</p>
        <p class="mt-1">Consent is required once per app session.</p>
        <p class="mt-1 text-xs">Some commands may be blocked by terminal security policy.</p>
        <button
          class="mt-4 rounded bg-amber-600 px-3 py-2 text-sm font-medium text-white hover:bg-amber-700"
          @click="grantConsent"
        >
          Enable terminal for this session
        </button>
      </div>
    </div>

    <template v-else>
      <div ref="scrollRef" class="min-h-0 flex-1 overflow-y-auto bg-[#0f172a] p-4 font-mono text-sm text-slate-100">
        <div v-if="entries.length === 0" class="text-slate-400">
          Terminal ready. Run commands with <code class="rounded bg-slate-800 px-1 py-0.5">Enter</code>.
        </div>
        <div v-for="(entry, idx) in entries" :key="idx" class="mb-3">
          <div v-if="entry.kind !== 'output'" class="text-sky-300">$ {{ entry.command }}</div>
          <div v-else class="text-xs uppercase tracking-wide text-slate-400">{{ entry.label || 'Output' }}</div>
          <pre v-if="entry.stdout" class="whitespace-pre-wrap break-words text-slate-100">{{ entry.stdout }}</pre>
          <pre v-if="entry.stderr" class="whitespace-pre-wrap break-words text-rose-300">{{ entry.stderr }}</pre>
          <div
            v-if="entry.kind !== 'output'"
            class="text-xs"
            :class="entry.exitCode === 0 ? 'text-emerald-400' : 'text-amber-400'"
          >
            exit {{ entry.exitCode }}
          </div>
        </div>
      </div>

      <div class="border-t border-gray-200 bg-white p-3">
        <div class="mb-2 flex items-center justify-between text-xs text-gray-600">
          <span>Shell: {{ shellLabel }}</span>
          <div class="flex items-center gap-2">
            <button
              class="rounded border border-gray-300 px-2 py-1 hover:bg-gray-50"
              @click="resetSession"
            >
              Reset Session
            </button>
            <button
              class="rounded border border-gray-300 px-2 py-1 hover:bg-gray-50"
              @click="clearTerminal"
            >
              Clear
            </button>
          </div>
        </div>
        <form class="flex items-center gap-2" @submit.prevent="runCommand">
          <input
            v-model="command"
            type="text"
            class="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            placeholder="Enter command (e.g., pwd, ls, pip install pandas==2.2.3)"
            :disabled="isRunning || !appStore.activeWorkspaceId"
          />
          <button
            type="submit"
            class="rounded bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-300"
            :disabled="isRunning || !command.trim() || !appStore.activeWorkspaceId"
          >
            {{ isRunning ? 'Running...' : 'Run' }}
          </button>
        </form>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { CommandLineIcon } from '@heroicons/vue/24/outline'
import { useAppStore } from '../../stores/appStore'
import apiService from '../../services/apiService'
import { toast } from '../../composables/useToast'

const appStore = useAppStore()

const command = ref('')
const entries = computed(() => appStore.terminalEntries || [])
const isRunning = ref(false)
const scrollRef = ref(null)
const shell = ref('')

const displayCwd = computed(() => appStore.terminalCwd || 'n/a')
const shellLabel = computed(() => {
  if (shell.value) return shell.value
  const p = navigator.platform.toLowerCase()
  if (p.includes('win')) return 'PowerShell/cmd'
  return 'bash/sh'
})

onMounted(async () => {
  await ensureWorkspaceCwd()
})

watch(() => appStore.activeWorkspaceId, async () => {
  await ensureWorkspaceCwd()
  clearTerminal()
})

async function ensureWorkspaceCwd() {
  if (!appStore.activeWorkspaceId) {
    appStore.setTerminalCwd('')
    return
  }
  try {
    const paths = await apiService.getDatabasePaths()
    if (paths?.base_directory) {
      appStore.setTerminalCwd(paths.base_directory)
    }
  } catch (_error) {
    // Keep terminal usable even if path lookup fails.
  }
}

function grantConsent() {
  appStore.setTerminalConsentGranted(true)
}

function clearTerminal() {
  appStore.clearTerminalEntries()
  appStore.setTerminalOutput('')
}

async function runCommand() {
  const raw = command.value.trim()
  if (!raw || !appStore.activeWorkspaceId || isRunning.value) return

  isRunning.value = true
  try {
    const payload = await apiService.executeTerminalCommand(appStore.activeWorkspaceId, {
      command: raw,
      cwd: appStore.terminalCwd || null,
      timeout: 180,
    })
    shell.value = payload?.shell || shell.value
    if (payload?.cwd) appStore.setTerminalCwd(payload.cwd)

    appStore.appendTerminalEntry({
      kind: 'command',
      source: 'terminal',
      command: raw,
      stdout: payload?.stdout || '',
      stderr: payload?.stderr || '',
      exitCode: Number.isInteger(payload?.exit_code) ? payload.exit_code : 1,
    })

    appStore.setTerminalOutput([payload?.stdout || '', payload?.stderr || ''].filter(Boolean).join('\n'))
    command.value = ''

    await nextTick()
    if (scrollRef.value) {
      scrollRef.value.scrollTop = scrollRef.value.scrollHeight
    }
  } catch (error) {
    const message = error?.message || 'Terminal execution failed.'
    appStore.appendTerminalEntry({
      kind: 'command',
      source: 'terminal',
      command: raw,
      stdout: '',
      stderr: message,
      exitCode: 1,
    })
    appStore.setTerminalOutput(message)
    toast.error('Terminal command failed', message)
  } finally {
    isRunning.value = false
  }
}

async function resetSession() {
  if (!appStore.activeWorkspaceId) return
  try {
    await apiService.resetTerminalSession(appStore.activeWorkspaceId)
    appStore.clearTerminalEntries()
    shell.value = ''
    await ensureWorkspaceCwd()
    toast.success('Terminal session reset', 'Started a fresh shell for this workspace.')
  } catch (error) {
    const message = error?.message || 'Failed to reset terminal session.'
    toast.error('Terminal reset failed', message)
  }
}
</script>
