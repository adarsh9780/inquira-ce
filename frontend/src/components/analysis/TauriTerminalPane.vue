<template>
  <div class="flex h-full min-h-0 flex-col overflow-hidden bg-white">
    <!-- Terminal Header (Teleported to RightPanel) -->
    <Teleport to="#terminal-toolbar" v-if="isMounted">
      <div class="flex items-center gap-3 text-[10px] sm:text-xs text-gray-600">
        <span class="rounded bg-gray-200 px-1.5 py-0.5 font-medium text-gray-700">{{ shellLabel }}</span>
        <span class="hidden md:inline font-mono truncate max-w-[150px]" :title="displayCwd">cwd: {{ displayCwd }}</span>
        <div class="flex items-center gap-1">
          <button 
            class="rounded border border-gray-300 px-2 py-0.5 bg-white hover:bg-gray-100 transition-colors" 
            @click="resetSession"
            title="Reset Session"
          >
            Reset
          </button>
          <button 
            class="rounded border border-gray-300 px-2 py-0.5 bg-white hover:bg-gray-100 transition-colors" 
            @click="clearScreen"
            title="Clear Screen"
          >
            Clear
          </button>
        </div>
      </div>
    </Teleport>

    <div class="flex-1 min-h-0 bg-[#0b1228] p-2">
      <div ref="terminalHostRef" class="h-full w-full"></div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'
import { useAppStore } from '../../stores/appStore'
import { toast } from '../../composables/useToast'
import tauriTerminalService from '../../services/tauriTerminalService'

const appStore = useAppStore()
const terminalHostRef = ref(null)
const sessionId = ref('')
const sessionCwd = ref('')
const shellLabel = ref('shell')
const isMounted = ref(false)

let terminal = null
let fitAddon = null
let dataDisposable = null
let resizeObserver = null
let sessionCleanup = null

const displayCwd = computed(() => sessionCwd.value || appStore.terminalCwd || 'n/a')

function normalizeErrorMessage(error, fallback) {
  if (!error) return fallback
  if (typeof error === 'string') return error
  if (typeof error?.message === 'string' && error.message.trim()) return error.message
  if (typeof error?.toString === 'function') {
    const rendered = String(error.toString() || '').trim()
    if (rendered && rendered !== '[object Object]') return rendered
  }
  return fallback
}

function buildSessionId() {
  const workspaceId = String(appStore.activeWorkspaceId || 'default')
  return `workspace:${workspaceId}`
}

async function stopSession() {
  if (sessionId.value) {
    try {
      await tauriTerminalService.stop(sessionId.value)
    } catch (_error) {
      // Best-effort during tab unmount/switch.
    }
  }
  if (typeof sessionCleanup === 'function') {
    await sessionCleanup()
  }
  sessionCleanup = null
  sessionId.value = ''
}

function writeBanner() {
  if (!terminal) return
  terminal.writeln('\x1b[90mInquira terminal ready.\x1b[0m')
}

async function startSession() {
  if (!terminal) return
  if (!appStore.activeWorkspaceId) {
    terminal.writeln('\x1b[33mNo active workspace selected.\x1b[0m')
    return
  }

  await stopSession()
  sessionId.value = buildSessionId()

  try {
    const response = await tauriTerminalService.startSession({
      sessionId: sessionId.value,
      cwd: appStore.terminalCwd || null,
      cols: terminal.cols,
      rows: terminal.rows,
      onData: (chunk) => {
        if (!terminal) return
        terminal.write(chunk)
      },
      onExit: () => {
        if (!terminal) return
        terminal.writeln('\r\n\x1b[90m[session ended]\x1b[0m')
      },
    })

    shellLabel.value = String(response?.shell || shellLabel.value)
    sessionCwd.value = String(response?.cwd || '')
    appStore.setTerminalCwd(sessionCwd.value)
    sessionCleanup = response?.dispose
    writeBanner()
  } catch (error) {
    const message = normalizeErrorMessage(error, 'Failed to start terminal session.')
    terminal.writeln(`\x1b[31m${message}\x1b[0m`)
    toast.error('Terminal startup failed', message)
  }
}

async function resetSession() {
  if (!terminal) return
  terminal.reset()
  await startSession()
}

function clearScreen() {
  if (!terminal) return
  terminal.clear()
}

onMounted(async () => {
  isMounted.value = true
  if (!tauriTerminalService.isTauriRuntime()) return
  if (!terminalHostRef.value) return

  terminal = new Terminal({
    cursorBlink: true,
    fontFamily: 'Menlo, Monaco, Consolas, "Courier New", monospace',
    fontSize: 13,
    theme: {
      background: '#0b1228',
      foreground: '#e2e8f0',
    },
    allowProposedApi: false,
    convertEol: true,
    scrollback: 10000,
  })

  fitAddon = new FitAddon()
  terminal.loadAddon(fitAddon)
  terminal.open(terminalHostRef.value)
  await nextTick()
  fitAddon.fit()

  dataDisposable = terminal.onData((chunk) => {
    if (!sessionId.value) return
    tauriTerminalService.write(sessionId.value, chunk).catch(() => {})
  })

  resizeObserver = new ResizeObserver(() => {
    if (!terminal || !fitAddon) return
    fitAddon.fit()
    if (!sessionId.value) return
    tauriTerminalService.resize(sessionId.value, terminal.cols, terminal.rows).catch(() => {})
  })
  resizeObserver.observe(terminalHostRef.value)

  await startSession()
})

watch(
  () => appStore.activeWorkspaceId,
  async () => {
    if (!terminal) return
    await startSession()
  },
)

onBeforeUnmount(async () => {
  if (dataDisposable) dataDisposable.dispose()
  if (resizeObserver && terminalHostRef.value) resizeObserver.unobserve(terminalHostRef.value)
  await stopSession()
  if (terminal) terminal.dispose()
  terminal = null
  fitAddon = null
})
</script>
