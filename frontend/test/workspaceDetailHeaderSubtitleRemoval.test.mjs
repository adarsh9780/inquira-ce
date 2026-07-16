import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('workspace detail header no longer shows primary dataset filename subtitle', () => {
  const tabPath = resolve(process.cwd(), 'src/components/modals/tabs/WorkspaceTab.vue')
  const source = readFileSync(tabPath, 'utf-8')

  assert.equal(source.includes('const primaryDatasetFilename = computed(() =>'), false)
  assert.equal(source.includes('<p v-if="primaryDatasetFilename"'), false)
  assert.equal(source.includes('<h4 class="section-label">Linked Datasets</h4>'), true)
})
