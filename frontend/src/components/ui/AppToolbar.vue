<template>
  <header class="app-toolbar" :aria-label="ariaLabel">
    <div class="app-toolbar-start"><slot name="start" /></div>
    <div class="app-toolbar-center"><slot /></div>
    <div class="app-toolbar-end"><slot name="end" /></div>
  </header>
</template>

<script setup>
defineProps({
  ariaLabel: { type: String, default: 'Toolbar' },
})
</script>
