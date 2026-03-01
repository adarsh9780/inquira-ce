<template>
  <div class="h-7 w-full bg-slate-50 border-t border-slate-200 flex items-center justify-between px-3 text-[11px] text-slate-600 select-none z-50 shrink-0">
    
    <!-- Left Section: Terminal & Kernel Status -->
    <div class="flex items-center gap-4 h-full">
      <!-- Terminal Toggle -->
      <button 
        @click="appStore.toggleTerminal()"
        class="flex items-center gap-1.5 h-full px-1.5 hover:bg-slate-200/50 hover:text-slate-900 transition-colors"
        :class="appStore.isTerminalOpen ? 'text-blue-600 font-medium' : ''"
        title="Toggle Terminal Panel"
      >
        <CommandLineIcon class="w-3.5 h-3.5" />
        <span>Terminal</span>
      </button>

      <!-- Vertical Divider -->
      <div class="w-px h-3.5 bg-slate-300"></div>

      <!-- Kernel Status -->
      <div class="flex items-center gap-1.5 h-full px-1">
        <span
          v-if="kernelStatusMeta.showSpinner"
          class="inline-block w-2 h-2 rounded-full border-[1.5px] border-blue-200 border-t-blue-600 animate-spin shrink-0"
          aria-hidden="true"
        ></span>
        <span v-else class="w-2 h-2 rounded-full shrink-0" :class="kernelStatusMeta.dotClass"></span>
        <span class="font-medium mr-2" :class="kernelStatusMeta.textClass">
          {{ kernelStatusMeta.label }}
        </span>

        <!-- Kernel Actions -->
        <div class="flex items-center gap-0.5 ml-1">
          <button
            @click="interruptKernel"
            :disabled="!appStore.activeWorkspaceId || isKernelActionRunning || kernelStatus === 'missing'"
            class="p-0.5 rounded hover:bg-slate-200 hover:text-amber-600 disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
            title="Interrupt Kernel"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-3.5 h-3.5"><path d="M5.25 3A2.25 2.25 0 003 5.25v9.5A2.25 2.25 0 005.25 17h9.5A2.25 2.25 0 0017 14.75v-9.5A2.25 2.25 0 0014.75 3h-9.5zM6 6.75a.75.75 0 01.75-.75h6.5a.75.75 0 01.75.75v6.5a.75.75 0 01-.75.75h-6.5a.75.75 0 01-.75-.75v-6.5z" /></svg>
          </button>
          <button
            @click="restartKernel"
            :disabled="!appStore.activeWorkspaceId || isKernelActionRunning"
            class="p-0.5 rounded hover:bg-slate-200 hover:text-red-500 disabled:opacity-30 disabled:hover:bg-transparent transition-colors"
            title="Restart Kernel"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-3.5 h-3.5"><path fill-rule="evenodd" d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z" clip-rule="evenodd" /></svg>
          </button>
        </div>
      </div>
    </div>

    <!-- Right Section: Editor Position & Version -->
    <div class="flex items-center gap-4 h-full">
      <div v-show="appStore.isEditorFocused" class="flex items-center text-slate-500 font-mono tracking-tight gap-1 pr-2">
        <span>Ln {{ appStore.editorLine }},</span>
        <span>Col {{ appStore.editorCol }}</span>
      </div>
      
      <!-- Version (Optional, thin) -->
      <a 
        href="https://github.com/adarsh9780/inquira" 
        target="_blank" 
        class="text-slate-400 hover:text-slate-600 transition-colors font-mono"
        title="View on GitHub"
      >
        Inquira v0.5.7
      </a>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useAppStore } from '../../stores/appStore'
import apiService from '../../services/apiService'
import { CommandLineIcon } from '@heroicons/vue/24/outline'
import { toast } from '../../composables/useToast'

const appStore = useAppStore()

// --- Kernel Status Management ---
const kernelStatus = ref('missing')
const isKernelStatusRequestInFlight = ref(false)
const isKernelActionRunning = ref(false)
let kernelStatusPoller = null

const kernelStatusMeta = computed(() => {
  switch (kernelStatus.value) {
    case 'ready':
      return { dotClass: 'bg-green-500', textClass: 'text-green-700', label: 'Kernel Ready', showSpinner: false }
    case 'busy':
      return { dotClass: 'bg-amber-500', textClass: 'text-amber-700', label: 'Kernel Busy', showSpinner: true }
    case 'starting':
    case 'connecting':
      return { dotClass: 'bg-blue-400', textClass: 'text-blue-600', label: 'Kernel Starting', showSpinner: true }
    case 'error':
      return { dotClass: 'bg-red-500', textClass: 'text-red-700', label: 'Kernel Error', showSpinner: false }
    case 'missing':
    default:
      return { dotClass: 'bg-gray-400', textClass: 'text-gray-500', label: 'No Kernel', showSpinner: false }
  }
})

async function refreshKernelStatus() {
  if (!appStore.activeWorkspaceId) {
    kernelStatus.value = 'missing'
    return
  }
  if (isKernelStatusRequestInFlight.value) return
  isKernelStatusRequestInFlight.value = true
  try {
    const status = await apiService.v1GetWorkspaceKernelStatus(appStore.activeWorkspaceId)
    kernelStatus.value = String(status?.status || 'missing').toLowerCase()
    if (['ready', 'busy', 'starting'].includes(kernelStatus.value)) {
      appStore.setRuntimeError('')
    }
  } catch (error) {
    kernelStatus.value = 'error'
    appStore.setRuntimeError(error?.response?.data?.detail || error?.message || 'Failed to fetch kernel status.')
  } finally {
    isKernelStatusRequestInFlight.value = false
  }
}

function startKernelStatusPolling() {
  stopKernelStatusPolling()
  refreshKernelStatus()
  kernelStatusPoller = setInterval(() => {
    if (!document.hidden) refreshKernelStatus()
  }, 5000)
}

function stopKernelStatusPolling() {
  if (kernelStatusPoller) {
    clearInterval(kernelStatusPoller)
    kernelStatusPoller = null
  }
}

async function interruptKernel() {
  if (!appStore.activeWorkspaceId || isKernelActionRunning.value) return
  isKernelActionRunning.value = true
  try {
    const response = await apiService.v1InterruptWorkspaceKernel(appStore.activeWorkspaceId)
    if (response?.reset) toast.success('Kernel Interrupted', 'Execution interrupt signal sent.')
    else toast.error('Interrupt Failed', 'No running kernel found.')
    await refreshKernelStatus()
  } catch (error) {
    toast.error('Interrupt Failed', error?.response?.data?.detail || error.message)
  } finally {
    isKernelActionRunning.value = false
  }
}

async function restartKernel() {
  if (!appStore.activeWorkspaceId || isKernelActionRunning.value) return
  isKernelActionRunning.value = true
  kernelStatus.value = 'connecting'
  try {
    const response = await apiService.v1RestartWorkspaceKernel(appStore.activeWorkspaceId)
    if (response?.reset) {
      appStore.setCodeRunning(false)
      toast.success('Kernel Restarted', 'Workspace kernel has been restarted.')
    } else {
      toast.error('Restart Failed', 'No kernel session existed.')
    }
    await refreshKernelStatus()
  } catch (error) {
    toast.error('Restart Failed', error?.response?.data?.detail || error.message)
    await refreshKernelStatus()
  } finally {
    isKernelActionRunning.value = false
  }
}

// Named handler so we can remove the exact same reference on unmount
function handleVisibilityChange() {
  if (!document.hidden && appStore.activeWorkspaceId) refreshKernelStatus()
}

// Lifecycle and Watchers
onMounted(() => {
  if (appStore.activeWorkspaceId) startKernelStatusPolling()
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onUnmounted(() => {
  stopKernelStatusPolling()
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})

watch(() => appStore.activeWorkspaceId, (newId) => {
  if (newId) startKernelStatusPolling()
  else stopKernelStatusPolling()
})
</script>
