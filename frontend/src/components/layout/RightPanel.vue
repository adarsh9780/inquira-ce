<template>
  <div class="flex h-full bg-white overflow-hidden">
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
import { useAppStore } from '../../stores/appStore'
import WorkspaceTab from './WorkspaceTab.vue'
import TableTab from '../analysis/TableTab.vue'
import FigureTab from '../analysis/FigureTab.vue'
import VariableExplorerTab from '../analysis/VariableExplorerTab.vue'
import TerminalTab from '../analysis/TerminalTab.vue'
import PreviewTab from '../preview/PreviewTab.vue'
import SchemaEditorTab from '../preview/SchemaEditorTab.vue'

const appStore = useAppStore()
</script>
