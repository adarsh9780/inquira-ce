<template>
  <div class="flex h-screen flex-col">
    <div class="app-shell-frame relative flex flex-1 overflow-hidden">
      <div class="app-nav-pane h-full shrink-0" :class="{ 'app-nav-pane-collapsed': sidebarCollapsed }">
        <UnifiedSidebar />
      </div>
      <div class="app-workspace-pane flex flex-1 flex-col overflow-hidden"><RightPanel /></div>
    </div>
    <StatusBar />
    <slot />
  </div>
</template>

<script setup lang="ts">
import RightPanel from './RightPanel.vue'
import StatusBar from './StatusBar.vue'
import UnifiedSidebar from './UnifiedSidebar.vue'

defineProps<{ sidebarCollapsed: boolean }>()
</script>
