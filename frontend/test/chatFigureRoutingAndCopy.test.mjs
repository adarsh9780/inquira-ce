import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat input routes chart-like responses to figure data pane', () => {
  const chatInputPath = resolve(process.cwd(), 'src/components/chat/ChatInput.vue')
  const source = readFileSync(chatInputPath, 'utf-8')

  assert.equal(source.includes('applyConversationResultState(requestConversationId, finalStatePatch, { hasFigures: true })'), true)
  assert.equal(source.includes("uiStore.setActiveTab('chart')"), false)
})

test('readiness and provider settings avoid provider-specific hardcoding in chat', () => {
  const chatInputPath = resolve(process.cwd(), 'src/components/chat/ChatInput.vue')
  const chatTabPath = resolve(process.cwd(), 'src/components/chat/ChatTab.vue')
  const llmTabPath = resolve(process.cwd(), 'src/components/modals/tabs/LLMSettingsTab.vue')

  const chatInput = readFileSync(chatInputPath, 'utf-8')
  const chatTab = readFileSync(chatTabPath, 'utf-8')
  const llmTab = readFileSync(llmTabPath, 'utf-8')

  assert.equal(chatInput.includes('Gemini API key'), false)
  assert.equal(chatTab.includes('Gemini API key'), false)
  assert.equal(chatInput.includes('OpenRouter API key'), false)
  assert.equal(chatTab.includes('OpenRouter API key'), false)
  assert.equal(chatInput.includes('<InlineNotice'), false)
  assert.equal(chatInput.includes('setupNotice'), false)
  assert.equal(chatInput.includes('missingSetupRequirements'), false)
  assert.equal(chatTab.includes('<WorkspaceReadinessJourney'), true)
  assert.equal(chatTab.includes("state === 'model_connection_required'"), true)
  assert.equal(chatTab.includes("uiStore.openSettings('connections')"), true)
  assert.equal(llmTab.includes('API Key (OpenRouter)'), false)
  assert.equal(llmTab.includes('{{ apiKeyLabel }}'), true)
})
