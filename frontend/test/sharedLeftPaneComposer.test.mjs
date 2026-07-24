import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('workspace left pane hosts the composer only for a ready chat view', () => {
  const leftPanePath = resolve(process.cwd(), 'src/components/layout/WorkspaceLeftPane.vue')
  const source = readFileSync(leftPanePath, 'utf-8')

  assert.equal(source.includes("import ChatInput from '../chat/ChatInput.vue'"), true)
  assert.equal(source.includes('<ChatInput />'), true)
  assert.equal(source.includes('<AppToolbar'), true)
  assert.equal(source.includes('<SegmentedControl'), true)
  assert.equal(source.includes('ChatBubbleLeftRightIcon'), true)
  assert.equal(source.includes('CodeBracketIcon'), true)
  assert.equal(source.includes('MagnifyingGlassIcon'), false)
  assert.equal(source.includes('CommandLineIcon'), false)
  assert.equal(source.includes("shortcutTitle('command-palette'"), false)
  assert.equal(source.includes('uiStore.openCommandPalette()'), false)
  assert.equal(source.includes('selectedWorkspacePane'), true)
  assert.equal(source.includes('rounded-xl border p-1'), false)
  assert.equal(source.includes('workspace-left-content-chat-only'), false)
  assert.equal(source.includes('workspaceLayoutMode'), false)
  assert.equal(source.includes("class=\"flex-shrink-0 pt-2\""), true)
  assert.equal(source.includes("v-if=\"uiStore.workspacePane === 'chat' && workspaceActivation.workspaceReadiness.ready\""), true)
  assert.equal(source.includes("v-show=\"uiStore.workspacePane === 'code'\""), true)
  assert.equal(source.includes("v-show=\"uiStore.workspacePane === 'chat'\""), true)
  assert.equal(source.includes("v-show=\"uiStore.workspacePane === 'ctree'\""), false)
  assert.equal(source.includes("uiStore.setWorkspacePane('ctree')"), false)
  assert.equal(source.includes('<SidebarGlobalTurnTree variant="page" />'), false)
})

test('chat tab keeps history content but no longer owns its own composer instance', () => {
  const chatTabPath = resolve(process.cwd(), 'src/components/chat/ChatTab.vue')
  const source = readFileSync(chatTabPath, 'utf-8')

  assert.equal(source.includes("import ChatInput from './ChatInput.vue'"), false)
  assert.equal(source.includes('<ChatInput />'), false)
  assert.equal(source.includes('data-chat-scroll-container'), true)
})
