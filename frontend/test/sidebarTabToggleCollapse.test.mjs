import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar tab icons toggle collapse when clicked again on active workspace/schema tabs', () => {
  const sidebarPath = resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue')
  const source = readFileSync(sidebarPath, 'utf-8')

  assert.equal(source.includes("@click=\"handleTabClick('workspace')\""), true)
  assert.equal(source.includes("@click=\"handleTabClick('schema-editor')\""), true)
  assert.equal(source.includes("if (normalized === 'workspace')"), true)
  assert.equal(source.includes("if (appStore.activeTab === 'workspace')"), true)
  assert.equal(source.includes("if (normalized === 'schema-editor')"), true)
  assert.equal(source.includes("if (appStore.activeTab === 'schema-editor')"), true)
  assert.equal(source.includes('appStore.setSidebarCollapsed(true)'), true)
})
