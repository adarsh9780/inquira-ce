<template>
  <div class="flex h-full flex-col bg-white">
    <div class="flex-shrink-0 border-b border-gray-200 bg-white px-4 py-3 flex items-center justify-between">
      <div class="inline-flex rounded-lg border border-gray-200 bg-gray-50 p-1">
        <button
          @click="appStore.setDataPane('table')"
          class="rounded-md px-3 py-1.5 text-sm font-medium transition-colors flex items-center gap-1.5"
          :class="appStore.dataPane === 'table' ? 'bg-white text-blue-700 shadow-sm' : 'text-gray-600 hover:text-gray-900'"
        >
          <TableCellsIcon class="w-4 h-4" />
          Table
          <span v-if="appStore.dataframes?.length" class="ml-1 inline-flex items-center justify-center bg-blue-100 text-blue-800 text-[10px] font-bold px-1.5 rounded-full min-w-[1.25rem]">{{ appStore.dataframes.length }}</span>
        </button>
        <button
          @click="appStore.setDataPane('figure')"
          class="rounded-md px-3 py-1.5 text-sm font-medium transition-colors flex items-center gap-1.5"
          :class="appStore.dataPane === 'figure' ? 'bg-white text-blue-700 shadow-sm' : 'text-gray-600 hover:text-gray-900'"
        >
          <ChartBarIcon class="w-4 h-4" />
          Figure
          <span v-if="appStore.figures?.length" class="ml-1 inline-flex items-center justify-center bg-purple-100 text-purple-800 text-[10px] font-bold px-1.5 rounded-full min-w-[1.25rem]">{{ appStore.figures.length }}</span>
        </button>
        <button
          @click="appStore.setDataPane('varex')"
          class="rounded-md px-3 py-1.5 text-sm font-medium transition-colors flex items-center gap-1.5"
          :class="appStore.dataPane === 'varex' ? 'bg-white text-blue-700 shadow-sm' : 'text-gray-600 hover:text-gray-900'"
        >
          <CircleStackIcon class="w-4 h-4" />
          Var Ex
          <span v-if="appStore.scalars?.length" class="ml-1 inline-flex items-center justify-center bg-emerald-100 text-emerald-800 text-[10px] font-bold px-1.5 rounded-full min-w-[1.25rem]">{{ appStore.scalars.length }}</span>
        </button>
      </div>
    </div>

    <div class="min-h-0 flex-1 p-3 sm:p-4 bg-gray-50/50">
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
