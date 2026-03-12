import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('figure toolbar uses flexible selector width and icon-only actions', () => {
  const figureTabPath = resolve(process.cwd(), 'src/components/analysis/FigureTab.vue')
  const source = readFileSync(figureTabPath, 'utf-8')

  assert.equal(source.includes('class="flex min-w-0 flex-1 items-center justify-end gap-2"'), true)
  assert.equal(source.includes('class="flex min-w-[10rem] flex-1 items-center"'), true)
  assert.equal(source.includes('style="max-width: min(34vw, 20rem);"'), true)
  assert.equal(source.includes(`:title="isDeletingArtifact ? 'Deleting chart' : 'Delete chart'"`), true)
  assert.equal(source.includes(`:title="isDownloading ? 'Exporting chart' : 'Export chart'"`), true)
  assert.equal(source.includes('ChevronDownIcon'), false)
  assert.equal(source.includes('hover:text-red-600'), true)
})

test('output toolbar keeps filter controls flexible and icon-assisted', () => {
  const outputTabPath = resolve(process.cwd(), 'src/components/analysis/OutputTab.vue')
  const source = readFileSync(outputTabPath, 'utf-8')

  assert.equal(source.includes('class="flex min-w-0 w-full items-center justify-end gap-2"'), true)
  assert.equal(source.includes('class="mr-auto text-xs tabular-nums"'), true)
  assert.equal(source.includes('FunnelIcon'), true)
  assert.equal(source.includes('class="flex min-w-[9rem] flex-1 items-center justify-end gap-2"'), true)
  assert.equal(source.includes('max-width: min(28vw, 11rem);'), true)
  assert.equal(source.includes('max-width-class="w-full"'), true)
})
