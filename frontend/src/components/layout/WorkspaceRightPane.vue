<template>
  <div class="flex h-full flex-col" style="background-color: var(--color-surface);">
    <div class="flex-shrink-0 h-16 border-b px-4 flex items-center gap-4" style="background-color: var(--color-base); border-color: var(--color-border);">
      <div class="inline-flex rounded-lg border p-1 flex-shrink-0" style="border-color: var(--color-border); background-color: var(--color-base);">
        <button
          @click="appStore.setDataPane('table')"
          class="rounded-md p-2 transition-colors flex items-center justify-center"
          :class="appStore.dataPane === 'table' ? 'bg-white shadow-sm' : ''"
          :style="appStore.dataPane === 'table' ? 'color: var(--color-text-main);' : 'color: var(--color-text-muted);'"
          title="Table"
          aria-label="Table"
        >
          <TableCellsIcon class="w-4 h-4" />
          <span class="sr-only">Table</span>
        </button>
        <button
          @click="appStore.setDataPane('figure')"
          class="rounded-md p-2 transition-colors flex items-center justify-center"
          :class="appStore.dataPane === 'figure' ? 'bg-white shadow-sm' : ''"
          :style="appStore.dataPane === 'figure' ? 'color: var(--color-text-main);' : 'color: var(--color-text-muted);'"
          title="Chart"
          aria-label="Chart"
        >
          <ChartBarIcon class="w-4 h-4" />
          <span class="sr-only">Chart</span>
        </button>
        <button
          @click="appStore.setDataPane('varex')"
          class="rounded-md p-2 transition-colors flex items-center justify-center"
          :class="appStore.dataPane === 'varex' ? 'bg-white shadow-sm' : ''"
          :style="appStore.dataPane === 'varex' ? 'color: var(--color-text-main);' : 'color: var(--color-text-muted);'"
          title="Var Ex"
          aria-label="Var Ex"
        >
          <CircleStackIcon class="w-4 h-4" />
          <span class="sr-only">Var Ex</span>
        </button>
      </div>
      
      <!-- Teleport Target for Table/Figure/VarEx Toolbar -->
      <div id="workspace-right-pane-toolbar" class="flex-1 min-w-0 flex items-center justify-end"></div>
    </div>

    <div class="min-h-0 flex-1 p-3 sm:p-4 pb-0" style="background-color: var(--color-base);">
      <div v-show="appStore.dataPane === 'table'" class="h-full">
        <TableTab />
      </div>
      <div v-show="appStore.dataPane === 'figure'" class="h-full">
        <FigureTab />
      </div>
      <div v-show="appStore.dataPane === 'varex'" class="h-full">
        <VariableExplorerTab />
      </div>
    </div>
  </div>
</template>

<script setup>
import { useAppStore } from '../../stores/appStore'
import TableTab from '../analysis/TableTab.vue'
import FigureTab from '../analysis/FigureTab.vue'
import VariableExplorerTab from '../analysis/VariableExplorerTab.vue'
import {
  TableCellsIcon,
  ChartBarIcon,
  CircleStackIcon
} from '@heroicons/vue/24/outline'

const appStore = useAppStore()
</script>
