import test from 'node:test'
import assert from 'node:assert/strict'
import viteConfig from '../vite.config.js'

test('vite dev server sets cross-origin isolation headers', () => {
  const headers = viteConfig.server?.headers
  assert.equal(headers['Cross-Origin-Opener-Policy'], 'same-origin')
  assert.equal(headers['Cross-Origin-Embedder-Policy'], 'require-corp')
  assert.equal(headers['Cross-Origin-Resource-Policy'], 'cross-origin')
})

test('vite preview server sets cross-origin isolation headers', () => {
  const headers = viteConfig.preview?.headers
  assert.equal(headers['Cross-Origin-Opener-Policy'], 'same-origin')
  assert.equal(headers['Cross-Origin-Embedder-Policy'], 'require-corp')
  assert.equal(headers['Cross-Origin-Resource-Policy'], 'cross-origin')
})
