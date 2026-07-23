<template>
  <div class="flex h-full flex-col overflow-hidden bg-[var(--color-base)]">
    <div v-if="!uiStore.terminalConsentGranted" class="flex-1 p-5">
      <div class="mx-auto max-w-xl rounded-lg border border-[var(--color-accent-border)] bg-[var(--color-warning-bg)] p-4 text-sm text-[var(--color-warning-text)]">
        <p class="font-semibold">Local terminal access</p>
        <p class="mt-2">Commands here run on your machine with your user permissions in the active workspace context. Terminal execution is not sandboxed.</p>
        <p class="mt-1">Consent is required before terminal use and is remembered for your account.</p>
        <button
          class="mt-4 rounded bg-[var(--color-warning)] px-3 py-2 text-sm font-medium text-[var(--color-on-accent)] hover:opacity-90"
          @click="uiStore.setTerminalConsentGranted(true)"
        >
          Enable terminal
        </button>
      </div>
    </div>

    <NativeTerminalPane v-else-if="nativeTerminalAvailable" />

    <div v-else class="flex flex-1 items-center justify-center p-6 text-center">
      <div>
        <p class="text-sm font-medium text-[var(--color-text-main)]">Terminal preview unavailable</p>
        <p class="mt-1 text-xs text-[var(--color-text-muted)]">The interactive terminal is available in the installed desktop app.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useUiStore } from '../../stores/uiStore'
import NativeTerminalPane from './NativeTerminalPane.vue'
import nativeTerminalService from '../../services/nativeTerminalService'

const uiStore = useUiStore()
const nativeTerminalAvailable = nativeTerminalService.isNativeRuntime()
</script>
