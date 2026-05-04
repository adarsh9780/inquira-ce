<template>
  <section class="scrollbar-hidden h-full overflow-y-auto">
    <h2 class="mb-2 text-lg font-bold text-[var(--color-text-main)]">Appearance</h2>
    <p class="mb-6 text-sm text-[var(--color-text-muted)]">
      Pick a UI theme. Each preview mirrors the shell hierarchy, not just the accent color.
    </p>

    <div class="mb-6 rounded-lg border border-[var(--color-border)] bg-[var(--color-base)] p-4">
      <label class="mb-2 block text-sm font-semibold text-[var(--color-text-main)]">Font</label>
      <p class="mb-3 text-xs text-[var(--color-text-muted)]">
        Switch between the current default font and Ubuntu.
      </p>
      <HeaderDropdown
        :model-value="activeFont"
        :options="fontOptions"
        placeholder="Select font"
        aria-label="UI font"
        max-width-class="w-full max-w-[260px]"
        @update:model-value="selectFont"
      />
    </div>

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

        <div
          class="mt-3 rounded-xl border p-2"
          :style="{ borderColor: theme.preview[1], backgroundColor: theme.preview[0] }"
        >
          <div class="flex h-20 overflow-hidden rounded-lg border" :style="{ borderColor: theme.preview[1] }">
            <div class="w-12 border-r px-2 py-2" :style="{ borderColor: theme.preview[1], backgroundColor: theme.preview[1] }">
              <div class="h-2 w-6 rounded-full" :style="{ backgroundColor: theme.preview[2] }"></div>
              <div class="mt-2 h-1.5 w-7 rounded-full bg-black/10"></div>
              <div class="mt-1.5 h-1.5 w-5 rounded-full bg-black/10"></div>
            </div>
            <div class="flex-1 px-3 py-2" :style="{ backgroundColor: theme.preview[0] }">
              <div class="flex items-center justify-between">
                <div class="h-2 w-16 rounded-full bg-black/10"></div>
                <div class="h-5 w-12 rounded-full" :style="{ backgroundColor: theme.preview[2] }"></div>
              </div>
              <div class="mt-3 grid grid-cols-2 gap-2">
                <div class="rounded-md border p-2" :style="{ borderColor: theme.preview[1], backgroundColor: 'color-mix(in srgb, white 35%, transparent)' }">
                  <div class="h-1.5 w-10 rounded-full bg-black/10"></div>
                  <div class="mt-2 h-4 w-full rounded-md" :style="{ backgroundColor: theme.preview[2] }"></div>
                </div>
                <div class="rounded-md border p-2" :style="{ borderColor: theme.preview[1], backgroundColor: 'color-mix(in srgb, black 4%, transparent)' }">
                  <div class="h-1.5 w-8 rounded-full bg-black/10"></div>
                  <div class="mt-2 h-4 w-full rounded-md bg-black/10"></div>
                </div>
              </div>
            </div>
          </div>
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
import HeaderDropdown from '../../ui/HeaderDropdown.vue'

const appStore = useAppStore()

const activeTheme = computed(() => appStore.uiTheme)
const themes = computed(() => appStore.availableThemes)
const activeFont = computed(() => appStore.uiFont)
const fontOptions = computed(() => {
  const options = Array.isArray(appStore.availableFonts) ? appStore.availableFonts : []
  return options.map((font) => ({
    value: font.id,
    label: font.label,
  }))
})

function selectTheme(themeId) {
  appStore.setUiTheme(themeId)
}

function selectFont(fontId) {
  appStore.setUiFont(fontId)
}
</script>
