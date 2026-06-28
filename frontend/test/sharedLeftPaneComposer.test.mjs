import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('workspace left pane hosts a shared chat composer below both code and chat views', () => {
  const leftPanePath = resolve(process.cwd(), 'src/components/layout/WorkspaceLeftPane.vue')
  const source = readFileSync(leftPanePath, 'utf-8')

  assert.equal(source.includes("import ChatInput from '../chat/ChatInput.vue'"), true)
  assert.equal(source.includes("import SidebarGlobalTurnTree from './sidebar/SidebarGlobalTurnTree.vue'"), true)
  assert.equal(source.includes('<ChatInput />'), true)
  assert.equal(source.includes('class="workspace-pane-tabs inline-flex items-center gap-1 flex-shrink-0"'), true)
  assert.equal(source.includes('ChatBubbleLeftRightIcon'), true)
  assert.equal(source.includes('CodeBracketIcon'), true)
  assert.equal(source.includes('ShareIcon'), true)
  assert.equal(source.includes('class="workspace-pane-tab"'), true)
  assert.equal(source.includes('workspace-pane-tab-active'), true)
  assert.equal(source.includes('rounded-xl border p-1'), false)
  assert.equal(source.includes("workspace-left-content-chat-only"), true)
  assert.equal(source.includes("const isChatOnlyMode = computed(() => appStore.workspacePane === 'chat' && appStore.workspaceLayoutMode === 'chat')"), true)
  assert.equal(source.includes("class=\"flex-shrink-0 pt-2 sm:pt-3\""), true)
  assert.equal(source.includes("v-show=\"appStore.workspacePane === 'code'\""), true)
  assert.equal(source.includes("v-show=\"appStore.workspacePane === 'chat'\""), true)
  assert.equal(source.includes("v-show=\"appStore.workspacePane === 'ctree'\""), true)
  assert.equal(source.includes("appStore.setWorkspacePane('ctree')"), true)
  assert.equal(source.includes('<SidebarGlobalTurnTree variant="page" />'), true)
})

test('chat tab keeps history content but no longer owns its own composer instance', () => {
  const chatTabPath = resolve(process.cwd(), 'src/components/chat/ChatTab.vue')
  const source = readFileSync(chatTabPath, 'utf-8')

  assert.equal(source.includes("import ChatInput from './ChatInput.vue'"), false)
  assert.equal(source.includes('<ChatInput />'), false)
  assert.equal(source.includes('data-chat-scroll-container'), true)
})
