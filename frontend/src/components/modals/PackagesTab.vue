<template>
  <div class="p-6">
    <h2 class="text-xl font-semibold mb-4 flex items-center">
      <CubeIcon class="w-6 h-6 mr-2 text-indigo-600" />
      Package Installation
    </h2>

    <div class="max-w-2xl rounded-md border p-4" style="border-color: var(--color-border); background-color: var(--color-surface);">
      <p class="text-sm font-medium" style="color: var(--color-text-main);">
        Install packages from Terminal
      </p>
      <p class="mt-1 text-xs" style="color: var(--color-text-muted);">
        Terminal gives full progress logs and complete error output, so package installation is easier to debug.
      </p>

      <div class="mt-3 space-y-2">
        <div class="text-xs" style="color: var(--color-text-muted);">Recommended command:</div>
        <code class="block text-xs rounded px-2 py-1" style="background-color: color-mix(in srgb, var(--color-border) 35%, transparent); color: var(--color-text-main);">
          uv pip install package==version
        </code>
      </div>

      <div class="mt-3">
        <button
          type="button"
          class="px-3 py-1.5 text-xs font-medium rounded-md btn-secondary"
          @click="openTerminal"
        >
          Open Terminal
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useAppStore } from '../../stores/appStore'
import { CubeIcon } from '@heroicons/vue/24/outline'

const appStore = useAppStore()

function openTerminal() {
  appStore.setActiveTab('workspace')
  if (!appStore.isTerminalOpen) {
    appStore.toggleTerminal()
  }
}
</script>
