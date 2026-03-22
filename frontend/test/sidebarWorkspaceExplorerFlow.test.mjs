import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar nests collapsible datasets and conversations under the selected workspace', () => {
  const unifiedSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'),
    'utf-8',
  )
  const datasetsSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/sidebar/SidebarDatasets.vue'),
    'utf-8',
  )
  const conversationsSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/sidebar/SidebarConversations.vue'),
    'utf-8',
  )

  assert.equal(unifiedSource.includes('<SidebarDatasets'), true)
  assert.equal(unifiedSource.includes('<SidebarConversations'), true)
  assert.equal(unifiedSource.includes('v-if="appStore.hasWorkspace"'), true)
  assert.equal(datasetsSource.includes('const isExpanded = ref(true)'), true)
  assert.equal(datasetsSource.includes(':class="isExpanded ? \'rotate-90\' : \'\'"'), true)
  assert.equal(conversationsSource.includes('const isExpanded = ref(true)'), true)
  assert.equal(conversationsSource.includes(':class="isExpanded ? \'rotate-90\' : \'\'"'), true)
})
