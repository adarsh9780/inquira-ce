import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function readSource(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('store exposes dataset-removal sync helpers for active selection cleanup', () => {
  const storeSource = readSource('src/stores/appStore.js')

  assert.equal(storeSource.includes('function clearActiveDatasetSelection() {'), true)
  assert.equal(storeSource.includes('function handleDatasetRemoved(tableName) {'), true)
  assert.equal(storeSource.includes('clearActiveDatasetSelection()'), true)
})

test('dataset delete entry points clear active selection and broadcast catalog refresh', () => {
  const sidebarSource = readSource('src/components/layout/UnifiedSidebar.vue')
  const workspaceTabSource = readSource('src/components/modals/tabs/WorkspaceTab.vue')

  assert.equal(sidebarSource.includes('appStore.handleDatasetRemoved(deletedTableName)'), true)
  assert.equal(sidebarSource.includes("window.dispatchEvent(new CustomEvent('dataset-switched', { detail: null }))"), true)
  assert.equal(sidebarSource.includes("appStore.activeDatasetId === ds.table_name"), false)
  assert.equal(sidebarSource.includes(":class=\"{ 'sidebar-item-row-active': isSelectedDataset(ds) }\""), true)

  assert.equal(workspaceTabSource.includes('appStore.handleDatasetRemoved(tableName)'), true)
  assert.equal(workspaceTabSource.includes("window.dispatchEvent(new CustomEvent('dataset-switched', { detail: null }))"), true)
})
