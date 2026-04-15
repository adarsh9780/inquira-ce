<template>
  <section class="h-full">
    <h2 class="mb-2 text-lg font-bold text-[var(--color-text-main)]">Appearance</h2>
    <p class="mb-4 text-sm text-[var(--color-text-muted)]">
      Pick a UI theme. Changes apply instantly and persist for future sessions.
    </p>

    <div class="space-y-2">
      <button
        v-for="theme in themes"
        :key="theme.id"
        type="button"
        class="w-full rounded-lg border px-4 py-3 text-left transition-colors"
        :class="theme.id === activeTheme
          ? 'border-[var(--color-accent-border)] bg-[var(--color-accent-soft)]'
          : 'border-[var(--color-border)] bg-[var(--color-base)] hover:bg-[var(--color-base-soft)]'"
        @click="selectTheme(theme.id)"
      >
        <div class="flex items-center justify-between gap-3">
          <div>
            <p class="text-sm font-semibold text-[var(--color-text-main)]">{{ theme.label }}</p>
            <p class="mt-1 text-xs text-[var(--color-text-muted)]">{{ theme.description }}</p>
          </div>
          <span
            v-if="theme.id === activeTheme"
            class="rounded-full border border-[var(--color-accent-border)] bg-[var(--color-base)] px-2 py-0.5 text-[11px] font-medium text-[var(--color-accent)]"
          >
            Active
          </span>
        </div>

        <div class="mt-3 flex items-center gap-1.5">
          <span
            v-for="color in theme.preview"
            :key="`${theme.id}-${color}`"
            class="h-3.5 w-3.5 rounded-full border border-[var(--color-border)]"
            :style="{ backgroundColor: color }"
          ></span>
        </div>
      </button>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { useAppStore } from '../../../stores/appStore'

const appStore = useAppStore()

const activeTheme = computed(() => appStore.uiTheme)
const themes = computed(() => appStore.availableThemes)

function selectTheme(themeId) {
  appStore.setUiTheme(themeId)
}
</script>
