import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('status bar keeps account controls first and uses sidebar-style drop-up menu content', () => {
  const statusBarSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/StatusBar.vue'),
    'utf-8',
  )
  const sidebarSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'),
    'utf-8',
  )

  assert.equal(statusBarSource.includes('toggleSidebarFromStatusBar'), true)
  assert.equal(statusBarSource.includes('toggleAccountMenu'), true)
  assert.equal(statusBarSource.includes('show sidebar (cmd/ctrl+b)'), false)
  assert.equal(statusBarSource.includes('Show sidebar (Cmd/Ctrl+B)'), true)
  assert.equal(statusBarSource.includes('Hide sidebar (Cmd/Ctrl+B)'), true)
  assert.equal(statusBarSource.includes('Toggle terminal panel (Cmd/Ctrl+J)'), true)
  assert.equal(statusBarSource.includes('Open account menu'), true)
  assert.equal(statusBarSource.includes('Close account menu'), true)
  assert.equal(statusBarSource.includes('aria-label="Toggle account menu"'), true)
  assert.equal(statusBarSource.includes('ChevronUpIcon'), true)
  assert.equal(statusBarSource.includes('ChevronDownIcon'), true)
  assert.equal(statusBarSource.includes('ChevronUpDownIcon'), false)
  assert.equal(statusBarSource.includes('ChevronRightIcon'), true)
  assert.equal(statusBarSource.includes('ChevronLeftIcon'), true)
  assert.equal(statusBarSource.includes('statusControlPillClass'), false)
  assert.equal(statusBarSource.includes('font-medium px-1 text-slate-700'), false)
  assert.equal(statusBarSource.includes('max-w-[120px] truncate px-1 text-blue-600'), true)
  assert.equal(statusBarSource.includes('max-w-[120px] truncate px-1 text-blue-600 text-left rounded hover:bg-slate-200/70 transition-colors'), true)
  assert.equal(statusBarSource.includes('accountDisplayLabel'), true)
  assert.equal(statusBarSource.includes("if (!value.includes(' '))"), true)
  assert.equal(statusBarSource.includes('WS Connection'), true)
  assert.equal(statusBarSource.includes('Kernel Status'), true)
  assert.equal(statusBarSource.includes('Ln {{ appStore.editorLine }}'), true)
  assert.equal(statusBarSource.includes('Col {{ appStore.editorCol }}'), true)
  assert.equal(statusBarSource.includes('Right Section: Terminal & Version'), true)
  assert.equal(statusBarSource.includes('<SettingsModal'), true)
  assert.equal(statusBarSource.includes('<ConfirmationModal'), true)
  assert.equal(
    statusBarSource.indexOf('ref="accountMenuRef"') < statusBarSource.indexOf('Toggle terminal panel (Cmd/Ctrl+J)'),
    true,
  )
  assert.equal(
    statusBarSource.indexOf('<!-- Kernel Status -->') < statusBarSource.indexOf('Ln {{ appStore.editorLine }}'),
    true,
  )
  assert.equal(
    statusBarSource.indexOf('Ln {{ appStore.editorLine }}') < statusBarSource.indexOf('Toggle terminal panel (Cmd/Ctrl+J)'),
    true,
  )
  assert.equal(
    statusBarSource.indexOf('Toggle terminal panel (Cmd/Ctrl+J)') < statusBarSource.indexOf('Inquira v0.5.7'),
    true,
  )

  assert.equal(sidebarSource.includes('Account & Settings'), false)
  assert.equal(sidebarSource.includes('toggleUserMenu'), false)
})
