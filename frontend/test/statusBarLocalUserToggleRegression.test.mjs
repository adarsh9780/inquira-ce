import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('status bar no longer exposes the local user sidebar toggle', () => {
  const statusBarSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/StatusBar.vue'),
    'utf-8',
  )

  assert.equal(statusBarSource.includes('@click.stop="toggleSidebarFromStatusBar"'), false)
  assert.equal(statusBarSource.includes('function toggleSidebarFromStatusBar() {'), false)
  assert.equal(statusBarSource.includes('accountDisplayLabel'), false)
  assert.equal(statusBarSource.includes('function openSidebar() {'), false)
})
