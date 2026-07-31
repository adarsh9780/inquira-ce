<template>
  <div
    class="inquira-data-grid-viewport"
    :class="{ 'inquira-data-grid-viewport--fill': fill }"
    data-inquira-table-viewport
    role="region"
    :aria-label="label"
    tabindex="0"
  >
    <slot />
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ label: string; fill?: boolean }>(), { fill: false })
</script>

<style scoped>
.inquira-data-grid-viewport {
  min-width: 0;
  overflow: auto;
  overscroll-behavior: contain;
  background: var(--color-base);
  scrollbar-gutter: stable;
  scrollbar-color: var(--color-border-hover) var(--color-panel-muted);
}

.inquira-data-grid-viewport--fill {
  min-height: 0;
  flex: 1;
}

.inquira-data-grid-viewport:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: -2px;
}
</style>
