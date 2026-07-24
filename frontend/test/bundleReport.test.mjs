import assert from 'node:assert/strict'
import test from 'node:test'

import {
  collectManifestClosure,
  evaluateBudgets,
  findManifestKey,
} from '../scripts/bundle-report.mjs'

const manifest = {
  'index.html': {
    file: 'assets/index.js',
    isEntry: true,
    imports: ['_vendor.js'],
  },
  '_vendor.js': {
    file: 'assets/vendor.js',
    imports: ['_shared.js'],
  },
  '_shared.js': {
    file: 'assets/shared.js',
    imports: ['_vendor.js'],
  },
  'src/FigureTab.vue': {
    file: 'assets/figure.js',
    isDynamicEntry: true,
    imports: ['_shared.js'],
  },
}

test('bundle report resolves a static manifest closure without cycles', () => {
  assert.deepEqual(
    collectManifestClosure(manifest, 'index.html'),
    ['index.html', '_vendor.js', '_shared.js'],
  )
})

test('bundle report finds entry and feature manifest keys', () => {
  assert.equal(findManifestKey(manifest, (_key, item) => item.isEntry), 'index.html')
  assert.equal(findManifestKey(manifest, (key) => key.endsWith('FigureTab.vue')), 'src/FigureTab.vue')
})

test('bundle budget evaluation reports individual failures', () => {
  const checks = evaluateBudgets(
    {
      entryFile: { gzipBytes: 120 },
      entry: { gzipBytes: 180 },
      plotlyChunk: { gzipBytes: 400 },
    },
    {
      entryFileGzipBytes: 100,
      initialClosureGzipBytes: 200,
      plotlyChunkGzipBytes: 450,
    },
  )

  assert.deepEqual(checks.map(({ name, passed }) => ({ name, passed })), [
    { name: 'entryFileGzipBytes', passed: false },
    { name: 'initialClosureGzipBytes', passed: true },
    { name: 'plotlyChunkGzipBytes', passed: true },
  ])
})
