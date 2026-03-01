<template>
  <div class="flex h-full flex-col overflow-hidden rounded-lg border" style="background-color: var(--color-base); border-color: var(--color-border);">
    <!-- Terminal Header (Teleported to RightPanel) -->
    <Teleport to="#terminal-toolbar" v-if="isMounted && !(useTauriPty && appStore.terminalConsentGranted)">
      <div class="flex items-center gap-2 text-[10px] sm:text-xs text-gray-600">
        <span class="rounded bg-gray-200 px-1.5 py-0.5 font-medium text-gray-700">{{ shellLabel }}</span>
        <span class="hidden md:inline font-mono truncate max-w-[150px]" :title="displayCwd">cwd: {{ displayCwd }}</span>
      </div>
    </Teleport>

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

    <template v-else-if="useTauriPty">
      <TauriTerminalPane />
    </template>

    <template v-else>
      <div
        ref="scrollRef"
        class="terminal-shell min-h-0 flex-1 overflow-y-auto bg-[#0b1228] p-4 font-mono text-sm text-slate-100"
        @click="focusCommandInput"
      >
        <div class="mb-2 text-slate-400">
          Terminal ready.
          <span class="text-slate-300">Enter</span> to run,
          <span class="text-slate-300">↑/↓</span> for history.
        </div>

        <div v-for="(entry, idx) in entries" :key="idx" class="mb-3">
          <template v-if="entry.kind !== 'output'">
            <div class="flex items-center gap-2">
              <span class="text-emerald-300">{{ promptPrefix }}</span>
              <span class="text-cyan-300">{{ entry.command }}</span>
            </div>
            <pre v-if="entry.stdout" class="whitespace-pre-wrap break-words text-slate-100">{{ entry.stdout }}</pre>
            <pre v-if="entry.stderr" class="whitespace-pre-wrap break-words text-rose-300">{{ entry.stderr }}</pre>
            <div class="text-xs" :class="entry.exitCode === 0 ? 'text-emerald-400' : 'text-amber-400'">
              exit {{ entry.exitCode }}
            </div>
          </template>
          <template v-else>
            <div class="text-xs uppercase tracking-wide text-slate-400">{{ entry.label || 'Output' }}</div>
            <pre v-if="entry.stdout" class="whitespace-pre-wrap break-words text-slate-100">{{ entry.stdout }}</pre>
            <pre v-if="entry.stderr" class="whitespace-pre-wrap break-words text-rose-300">{{ entry.stderr }}</pre>
          </template>
        </div>

        <div v-if="isRunning && liveCommand" class="mb-3">
          <div class="flex items-center gap-2">
            <span class="text-emerald-300">{{ promptPrefix }}</span>
            <span class="text-cyan-300">{{ liveCommand }}</span>
          </div>
          <pre v-if="liveStdout" class="whitespace-pre-wrap break-words text-slate-100">{{ liveStdout }}</pre>
          <pre v-if="liveStderr" class="whitespace-pre-wrap break-words text-rose-300">{{ liveStderr }}</pre>
          <div class="text-xs text-amber-400">running...</div>
        </div>

        <form class="mt-2 border-t border-slate-700/70 pt-3" @submit.prevent="runCommand">
          <div class="flex items-center gap-2">
            <span class="text-emerald-300">{{ promptPrefix }}</span>
            <input
              ref="commandInputRef"
              v-model="command"
              type="text"
              class="w-full bg-transparent text-slate-100 outline-none placeholder:text-slate-500 caret-emerald-300"
              placeholder="type command..."
              autocomplete="off"
              spellcheck="false"
              :disabled="isRunning || !appStore.activeWorkspaceId"
              @keydown="handleInputKeydown"
            />
          </div>
        </form>
      </div>

      <div class="border-t px-3 py-2" style="border-color: var(--color-border); background-color: var(--color-base);">
        <div class="flex items-center justify-between text-xs" style="color: var(--color-text-muted);">
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
import TauriTerminalPane from './TauriTerminalPane.vue'

const appStore = useAppStore()
const isMounted = ref(false)

const command = ref('')
const entries = computed(() => appStore.terminalEntries || [])
const isRunning = ref(false)
const scrollRef = ref(null)
const shell = ref('')
const liveCommand = ref('')
const liveStdout = ref('')
const liveStderr = ref('')
const commandInputRef = ref(null)
const commandHistory = ref([])
const commandHistoryIndex = ref(-1)
const useTauriPty = typeof window !== 'undefined' && !!window.__TAURI_INTERNALS__

const displayCwd = computed(() => appStore.terminalCwd || 'n/a')
const promptPrefix = computed(() => `${(displayCwd.value || '~').split('/').pop() || '~'} $`)
const shellLabel = computed(() => {
  if (shell.value) return shell.value
  const p = navigator.platform.toLowerCase()
  if (p.includes('win')) return 'PowerShell/cmd'
  return 'bash/sh'
})

onMounted(async () => {
  isMounted.value = true
  await ensureWorkspaceCwd()
  if (!useTauriPty) {
    focusCommandInput()
  }
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
  focusCommandInput()
}

function focusCommandInput() {
  if (!commandInputRef.value) return
  commandInputRef.value.focus()
}

function handleInputKeydown(event) {
  if (event.key === 'ArrowUp') {
    event.preventDefault()
    if (commandHistory.value.length === 0) return
    if (commandHistoryIndex.value < 0) {
      commandHistoryIndex.value = commandHistory.value.length - 1
    } else if (commandHistoryIndex.value > 0) {
      commandHistoryIndex.value -= 1
    }
    command.value = commandHistory.value[commandHistoryIndex.value] || ''
    return
  }
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    if (commandHistory.value.length === 0 || commandHistoryIndex.value < 0) return
    if (commandHistoryIndex.value < commandHistory.value.length - 1) {
      commandHistoryIndex.value += 1
      command.value = commandHistory.value[commandHistoryIndex.value] || ''
      return
    }
    commandHistoryIndex.value = -1
    command.value = ''
  }
}

async function runCommand() {
  const raw = command.value.trim()
  if (!raw || !appStore.activeWorkspaceId || isRunning.value) return

  isRunning.value = true
  commandHistory.value.push(raw)
  commandHistoryIndex.value = -1
  liveCommand.value = raw
  liveStdout.value = ''
  liveStderr.value = ''
  try {
    const payload = await apiService.executeTerminalCommandStream(
      appStore.activeWorkspaceId,
      {
        command: raw,
        cwd: appStore.terminalCwd || null,
        timeout: 180,
      },
      {
        onEvent: async (evt) => {
          if (evt?.event === 'output') {
            const line = String(evt?.data?.line || '')
            if (line) {
              liveStdout.value = liveStdout.value ? `${liveStdout.value}\n${line}` : line
              await nextTick()
              if (scrollRef.value) {
                scrollRef.value.scrollTop = scrollRef.value.scrollHeight
              }
            }
          } else if (evt?.event === 'error') {
            const detail = String(evt?.data?.detail || '')
            if (detail) {
              liveStderr.value = detail
            }
          }
        },
      },
    )
    shell.value = payload?.shell || shell.value
    if (payload?.cwd) appStore.setTerminalCwd(payload.cwd)

    appStore.appendTerminalEntry({
      kind: 'command',
      source: 'terminal',
      command: raw,
      stdout: payload?.stdout || liveStdout.value || '',
      stderr: payload?.stderr || liveStderr.value || '',
      exitCode: Number.isInteger(payload?.exit_code) ? payload.exit_code : 1,
    })

    appStore.setTerminalOutput([
      payload?.stdout || liveStdout.value || '',
      payload?.stderr || liveStderr.value || '',
    ].filter(Boolean).join('\n'))
    command.value = ''
    liveCommand.value = ''
    liveStdout.value = ''
    liveStderr.value = ''

    await nextTick()
    if (scrollRef.value) {
      scrollRef.value.scrollTop = scrollRef.value.scrollHeight
    }
    focusCommandInput()
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
    liveCommand.value = ''
    liveStdout.value = ''
    liveStderr.value = ''
    isRunning.value = false
    focusCommandInput()
  }
}

async function resetSession() {
  if (!appStore.activeWorkspaceId) return
  try {
    await apiService.resetTerminalSession(appStore.activeWorkspaceId)
    appStore.clearTerminalEntries()
    shell.value = ''
    await ensureWorkspaceCwd()
    commandHistory.value = []
    commandHistoryIndex.value = -1
    command.value = ''
    focusCommandInput()
    toast.success('Terminal session reset', 'Started a fresh shell for this workspace.')
  } catch (error) {
    const message = error?.message || 'Failed to reset terminal session.'
    toast.error('Terminal reset failed', message)
  }
}
</script>

<style scoped>
.terminal-shell {
  background-image:
    radial-gradient(circle at 25% 15%, rgba(56, 189, 248, 0.07), transparent 30%),
    radial-gradient(circle at 80% 85%, rgba(16, 185, 129, 0.05), transparent 35%);
}
</style>
