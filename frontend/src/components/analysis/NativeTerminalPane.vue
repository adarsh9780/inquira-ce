<template>
  <div class="flex h-full min-h-0 flex-col overflow-hidden" style="background-color: var(--color-base);">
    <!-- Terminal Header (Teleported to RightPanel) -->
    <Teleport to="#terminal-toolbar" v-if="isMounted">
      <div class="flex items-center gap-1.5 text-[10px]" style="color: var(--color-text-muted);">
        <span class="rounded px-1.5 py-0.5 font-medium" style="background-color: color-mix(in srgb, var(--color-text-main) 8%, transparent); color: var(--color-text-main);">{{ shellLabel }}</span>
        <span class="hidden md:inline font-mono truncate max-w-[150px]" :title="displayCwd">cwd: {{ displayCwd }}</span>
        <div class="flex items-center gap-1">
          <button
            class="btn-icon h-5 w-5 p-1 rounded-md"
            style="color: var(--color-text-muted);"
            @click="resetSession"
            title="Reset terminal session"
            aria-label="Reset terminal session"
          >
            <ArrowPathIcon class="h-3.5 w-3.5" />
          </button>
          <button
            class="btn-icon h-5 w-5 p-1 rounded-md"
            style="color: var(--color-text-muted);"
            @click="clearScreen"
            title="Clear terminal output"
            aria-label="Clear terminal output"
          >
            <TrashIcon class="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </Teleport>

    <div class="flex-1 min-h-0 p-2" style="background-color: var(--color-base);">
      <div ref="terminalHostRef" class="h-full w-full"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'
import { ArrowPathIcon, TrashIcon } from '@heroicons/vue/24/outline'
import { useUiStore } from '../../stores/uiStore'
import { usePreferencesStore } from '../../stores/preferencesStore'
import { useArtifactStore } from '../../stores/artifactStore'
import { useExecutionStore } from '../../stores/executionStore'
import { useWorkspaceStore } from '../../stores/workspaceStore'
import { useConversationStore } from '../../stores/conversationStore'
import { useWorkspaceActivation } from '../../composables/useWorkspaceActivation'
import { useArtifactPresentation } from '../../composables/useArtifactPresentation'
import { toast } from '../../composables/useToast'
import nativeTerminalService from '../../services/nativeTerminalService'

const uiStore = useUiStore()
const preferencesStore = usePreferencesStore()
const artifactStore = useArtifactStore()
const executionStore = useExecutionStore()
const workspaceStore = useWorkspaceStore()
const conversationStore = useConversationStore()
const workspaceActivation = useWorkspaceActivation()
const artifactPresentation = useArtifactPresentation()
const terminalHostRef = ref<any>(null)
const sessionId = ref('')
const sessionCwd = ref('')
const shellLabel = ref('shell')
const isMounted = ref(false)

let terminal: any = null
let fitAddon: any = null
let dataDisposable: { dispose(): void } | null = null
let resizeObserver: ResizeObserver | null = null
let sessionCleanup: (() => void | Promise<void>) | null = null

const displayCwd = computed(() => sessionCwd.value || uiStore.terminalCwd || 'n/a')

function readThemeColor(tokenName: any, fallback: any) {
  if (typeof window === 'undefined') return fallback
  const value = String(getComputedStyle(document.documentElement).getPropertyValue(tokenName) || '').trim()
  return value || fallback
}

function readThemeFont(tokenName: any, fallback: any) {
  if (typeof window === 'undefined') return fallback
  const value = String(getComputedStyle(document.documentElement).getPropertyValue(tokenName) || '').trim()
  return value || fallback
}

function getTerminalVisualTheme() {
  return {
    background: readThemeColor('--color-base', 'var(--color-base)'),
    foreground: readThemeColor('--color-text-main', 'var(--color-text-main)'),
    cursor: readThemeColor('--color-accent', 'var(--color-accent)'),
    selectionBackground: readThemeColor(
      '--color-info-bg',
      'color-mix(in srgb, var(--color-info) 18%, transparent)',
    ),
  }
}

function syncTerminalTheme() {
  if (!terminal) return
  terminal.options.theme = getTerminalVisualTheme()
  terminal.options.fontFamily = readThemeFont(
    '--font-mono',
    '"JetBrainsMono Nerd Font", "JetBrains Mono", monospace',
  )
}

function normalizeErrorMessage(error: any, fallback: any) {
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
  const workspaceId = String(workspaceStore.activeWorkspaceId || 'default')
  return `workspace:${workspaceId}`
}

async function stopSession() {
  if (sessionId.value) {
    try {
      await nativeTerminalService.stop(sessionId.value)
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
  if (!workspaceStore.activeWorkspaceId) {
    terminal.writeln('\x1b[33mNo active workspace selected.\x1b[0m')
    return
  }

  await stopSession()
  sessionId.value = buildSessionId()

  try {
    const response: any = await nativeTerminalService.startSession({
      workspaceId: workspaceStore.activeWorkspaceId,
      sessionId: sessionId.value,
      cwd: uiStore.terminalCwd || null,
      cols: terminal.cols,
      rows: terminal.rows,
      onData: (chunk: any) => {
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
    uiStore.setTerminalCwd(sessionCwd.value)
    sessionCleanup = response?.dispose
    writeBanner()
  } catch (error: any) {
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
  if (!nativeTerminalService.isNativeRuntime()) return
  if (!terminalHostRef.value) return

  const terminalFontFamily = readThemeFont('--font-mono', '"JetBrainsMono Nerd Font", "JetBrains Mono", monospace')

  terminal = new Terminal({
    cursorBlink: true,
    fontFamily: terminalFontFamily,
    fontSize: 13,
    theme: getTerminalVisualTheme(),
    allowProposedApi: false,
    convertEol: true,
    scrollback: 10000,
  })

  fitAddon = new FitAddon()
  terminal.loadAddon(fitAddon)
  terminal.open(terminalHostRef.value)
  await nextTick()
  fitAddon.fit()

  dataDisposable = terminal.onData((chunk: any) => {
    if (!sessionId.value) return
    nativeTerminalService.write(sessionId.value, chunk).catch(() => {})
  })

  resizeObserver = new ResizeObserver(() => {
    if (!terminal || !fitAddon) return
    fitAddon.fit()
    if (!sessionId.value) return
    nativeTerminalService.resize(sessionId.value, terminal.cols, terminal.rows).catch(() => {})
  })
  resizeObserver.observe(terminalHostRef.value)

  await startSession()
})

watch(
  () => workspaceStore.activeWorkspaceId,
  async () => {
    if (!terminal) return
    await startSession()
  },
)

watch(
  () => [preferencesStore.uiTheme, preferencesStore.uiCodeFont],
  async () => {
    await nextTick()
    syncTerminalTheme()
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
