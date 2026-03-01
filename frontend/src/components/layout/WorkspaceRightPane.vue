<template>
  <div class="flex h-full flex-col" style="background-color: var(--color-surface);">
    <div class="flex-shrink-0 border-b px-4 py-2 flex items-center justify-between" style="background-color: var(--color-base); border-color: var(--color-border);">
      <div class="inline-flex rounded-lg border p-1 flex-shrink-0" style="border-color: var(--color-border); background-color: var(--color-base);">
        <button
          @click="appStore.setDataPane('table')"
          class="rounded-md px-3 py-1.5 text-sm font-medium transition-colors flex items-center gap-1.5"
          :class="appStore.dataPane === 'table' ? 'bg-white shadow-sm' : ''"
          :style="appStore.dataPane === 'table' ? 'color: var(--color-text-main);' : 'color: var(--color-text-muted);'"
        >
          <TableCellsIcon class="w-4 h-4" />
          Table
          <span v-if="appStore.dataframes?.length" class="ml-1 inline-flex items-center justify-center text-[10px] font-bold px-1.5 rounded-full min-w-[1.25rem]" style="background-color: color-mix(in srgb, var(--color-text-main) 10%, transparent); color: var(--color-text-main);">{{ appStore.dataframes.length }}</span>
        </button>
        <button
          @click="appStore.setDataPane('figure')"
          class="rounded-md px-3 py-1.5 text-sm font-medium transition-colors flex items-center gap-1.5"
          :class="appStore.dataPane === 'figure' ? 'bg-white shadow-sm' : ''"
          :style="appStore.dataPane === 'figure' ? 'color: var(--color-text-main);' : 'color: var(--color-text-muted);'"
        >
          <ChartBarIcon class="w-4 h-4" />
          Figure
          <span v-if="appStore.figures?.length" class="ml-1 inline-flex items-center justify-center text-[10px] font-bold px-1.5 rounded-full min-w-[1.25rem]" style="background-color: color-mix(in srgb, var(--color-text-main) 10%, transparent); color: var(--color-text-main);">{{ appStore.figures.length }}</span>
        </button>
        <button
          @click="appStore.setDataPane('varex')"
          class="rounded-md px-3 py-1.5 text-sm font-medium transition-colors flex items-center gap-1.5"
          :class="appStore.dataPane === 'varex' ? 'bg-white shadow-sm' : ''"
          :style="appStore.dataPane === 'varex' ? 'color: var(--color-text-main);' : 'color: var(--color-text-muted);'"
        >
          <CircleStackIcon class="w-4 h-4" />
          Var Ex
          <span v-if="appStore.scalars?.length" class="ml-1 inline-flex items-center justify-center text-[10px] font-bold px-1.5 rounded-full min-w-[1.25rem]" style="background-color: color-mix(in srgb, var(--color-text-main) 10%, transparent); color: var(--color-text-main);">{{ appStore.scalars.length }}</span>
        </button>
      </div>
      
      <!-- Teleport Target for Table/Figure/VarEx Toolbar -->
      <div id="workspace-right-pane-toolbar" class="flex-1 min-w-0 flex items-center justify-end ml-4"></div>
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
