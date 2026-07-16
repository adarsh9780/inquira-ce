import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('native splash mirrors in-app loading shell structure', () => {
  const splashSource = readFileSync(
    resolve(process.cwd(), 'public/splash.html'),
    'utf-8',
  )

  assert.equal(splashSource.includes('src="/favicon.svg"'), true)
  assert.equal(splashSource.includes('Starting Inquira.'), true)
  assert.equal(splashSource.includes('class="progress-track"'), true)
  assert.equal(splashSource.includes('class="status-label">Starting</span>'), true)
  assert.equal(splashSource.includes('backend APIs are healthy'), true)
})
