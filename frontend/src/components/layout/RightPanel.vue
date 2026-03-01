<template>
  <div class="flex h-full bg-white overflow-hidden">
    <div
      class="border-r border-gray-100 bg-gradient-to-b from-gray-50 to-slate-50 p-2 sm:p-3 transition-all duration-200"
      :class="appStore.isSidebarCollapsed ? 'w-14 sm:w-14 lg:w-14' : 'w-40 sm:w-44 lg:w-48'"
    >
      <div class="mb-2 flex items-center justify-between">
        <span v-if="!appStore.isSidebarCollapsed" class="ml-1 text-xs font-semibold text-gray-500">Views</span>
        <button
          class="ml-auto rounded-md p-1.5 text-gray-600 hover:bg-gray-200"
          :title="appStore.isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"
          @click="appStore.setSidebarCollapsed(!appStore.isSidebarCollapsed)"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="h-5 w-5">
            <path v-if="appStore.isSidebarCollapsed" fill-rule="evenodd" d="M3 12a1 1 0 011-1h11.586l-3.293-3.293a1 1 0 111.414-1.414l5 5a1 1 0 010 1.414l-5 5a1 1 0 11-1.414-1.414L15.586 13H4a1 1 0 01-1-1z" clip-rule="evenodd" />
            <path v-else fill-rule="evenodd" d="M21 12a1 1 0 01-1 1H8.414l3.293 3.293a1 1 0 11-1.414 1.414l-5-5a1 1 0 010-1.414l5-5a1 1 0 111.414 1.414L8.414 11H20a1 1 0 011 1z" clip-rule="evenodd" />
          </svg>
        </button>
      </div>

      <nav class="flex flex-col space-y-2" aria-label="Tabs">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          @click="appStore.setActiveTab(tab.id)"
          :class="[
            appStore.activeTab === tab.id
              ? 'bg-white text-blue-600 shadow-lg border-blue-200'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200 hover:text-gray-800 border-gray-200',
            'relative w-full border rounded-lg sm:rounded-xl font-semibold text-sm transition-all duration-200 flex items-center leading-none',
            appStore.isSidebarCollapsed ? 'h-12 aspect-square justify-center p-3' : 'py-3 px-3 justify-start',
            flash[tab.id] ? 'ring-2 ring-green-400 ring-offset-1 animate-pulse' : ''
          ]"
          :title="tab.name"
        >
          <div class="relative flex w-full items-center" :class="appStore.isSidebarCollapsed ? 'justify-center' : 'justify-start'">
            <component :is="tab.icon" class="h-5 w-5 flex-shrink-0" />
            <span v-show="!appStore.isSidebarCollapsed" class="ml-2 whitespace-nowrap text-sm font-medium">{{ tab.name }}</span>

            <span v-if="appStore.isSidebarCollapsed && tab.count && Number(tab.count) > 0"
                  class="absolute right-1 top-1 inline-flex h-5 min-w-[18px] items-center justify-center rounded-full px-1 text-[10px] font-bold text-white shadow-md ring-2 ring-white"
                  :class="tab.badgeColor">
              {{ tab.count }}
            </span>
            <span v-else-if="!appStore.isSidebarCollapsed && tab.count && Number(tab.count) > 0"
                  class="ml-auto inline-flex items-center rounded-full px-2 py-1 text-xs font-bold shadow-sm"
                  :class="tab.badgeClass">
              {{ tab.count }}
            </span>
          </div>
        </button>
      </nav>
    </div>

    <div class="relative flex-1 overflow-hidden bg-gray-50/50">
      <div v-show="appStore.activeTab === 'workspace'" class="h-full">
        <WorkspaceTab />
      </div>
      <div v-show="appStore.activeTab === 'table'" class="h-full p-3 sm:p-4">
        <TableTab />
      </div>
      <div v-show="appStore.activeTab === 'figure'" class="h-full p-3 sm:p-4">
        <FigureTab />
      </div>
      <div v-show="appStore.activeTab === 'varex'" class="h-full p-3 sm:p-4">
        <VariableExplorerTab />
      </div>
      <div v-show="appStore.activeTab === 'terminal'" class="h-full p-3 sm:p-4">
        <TerminalTab />
      </div>
      <div v-show="appStore.activeTab === 'preview'" class="h-full p-3 sm:p-4">
        <PreviewTab />
      </div>
      <div v-show="appStore.activeTab === 'schema-editor'" class="h-full p-3 sm:p-4">
        <SchemaEditorTab />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useAppStore } from '../../stores/appStore'
import WorkspaceTab from './WorkspaceTab.vue'
import TableTab from '../analysis/TableTab.vue'
import FigureTab from '../analysis/FigureTab.vue'
import VariableExplorerTab from '../analysis/VariableExplorerTab.vue'
import TerminalTab from '../analysis/TerminalTab.vue'
import PreviewTab from '../preview/PreviewTab.vue'
import SchemaEditorTab from '../preview/SchemaEditorTab.vue'
import {
  RectangleGroupIcon,
  TableCellsIcon,
  ChartBarIcon,
  CommandLineIcon,
  CircleStackIcon,
  DocumentTextIcon,
  EyeIcon,
} from '@heroicons/vue/24/outline'

const appStore = useAppStore()

const tabs = computed(() => [
  {
    id: 'workspace',
    name: 'Workspace',
    icon: RectangleGroupIcon,
    count: null,
    badgeClass: '',
    badgeColor: 'bg-blue-600',
  },
  {
    id: 'table',
    name: 'Table',
    icon: TableCellsIcon,
    count: appStore.dataframes?.length ? String(appStore.dataframes.length) : null,
    badgeClass: appStore.dataframes?.length ? 'bg-blue-100 text-blue-800' : '',
    badgeColor: 'bg-sky-600',
  },
  {
    id: 'figure',
    name: 'Figure',
    icon: ChartBarIcon,
    count: appStore.figures?.length ? String(appStore.figures.length) : null,
    badgeClass: appStore.figures?.length ? 'bg-purple-100 text-purple-800' : '',
    badgeColor: 'bg-fuchsia-600',
  },
  {
    id: 'varex',
    name: 'VarEx',
    icon: CircleStackIcon,
    count: appStore.scalars?.length ? String(appStore.scalars.length) : null,
    badgeClass: appStore.scalars?.length ? 'bg-emerald-100 text-emerald-800' : '',
    badgeColor: 'bg-emerald-600',
  },
  ...(appStore.terminalEnabled ? [{
    id: 'terminal',
    name: 'Terminal',
    icon: CommandLineIcon,
    count: appStore.terminalOutput && !appStore.isCodeRunning ? '1' : null,
    badgeClass: appStore.terminalOutput && !appStore.isCodeRunning ? 'bg-gray-100 text-gray-800' : '',
    badgeColor: 'bg-slate-700',
  }] : []),
  {
    id: 'preview',
    name: 'Preview',
    icon: EyeIcon,
    count: null,
    badgeClass: '',
    badgeColor: 'bg-gray-400',
  },
  {
    id: 'schema-editor',
    name: 'Schema',
    icon: DocumentTextIcon,
    count: null,
    badgeClass: '',
    badgeColor: 'bg-gray-400',
  },
])

const flash = ref({})
const counts = computed(() => ({
  workspace: appStore.workspacePane === 'chat' ? appStore.chatHistory?.length || 0 : (!appStore.isCodeRunning && appStore.generatedCode ? 1 : 0),
  table: appStore.dataframes?.length || 0,
  figure: appStore.figures?.length || 0,
  varex: appStore.scalars?.length || 0,
  terminal: appStore.terminalOutput && !appStore.isCodeRunning ? 1 : 0,
}))

watch(counts, (n, o) => {
  if (!o) return
  for (const k of Object.keys(n)) {
    if ((n[k] || 0) > (o[k] || 0)) {
      flash.value = { ...flash.value, [k]: true }
      setTimeout(() => {
        flash.value = { ...flash.value, [k]: false }
      }, 1000)
    }
  }
}, { deep: true })
</script>
