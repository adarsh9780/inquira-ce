import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('dataset switcher only shows selectable datasets without unsupported refresh/delete actions', () => {
  const switcherPath = resolve(process.cwd(), 'src/components/DatasetSwitcher.vue')
  const source = readFileSync(switcherPath, 'utf-8')

  assert.equal(source.includes('promptDelete('), false)
  assert.equal(source.includes('promptRefresh('), false)
  assert.equal(source.includes('confirmDelete('), false)
  assert.equal(source.includes('confirmRefresh('), false)
  assert.equal(source.includes('Delete Dataset'), false)
  assert.equal(source.includes('Refresh Dataset'), false)
  assert.equal(source.includes('Not Available Yet'), false)
})
