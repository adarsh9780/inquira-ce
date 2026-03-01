import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat input routes chart-like responses to figure data pane', () => {
  const chatInputPath = resolve(process.cwd(), 'src/components/chat/ChatInput.vue')
  const source = readFileSync(chatInputPath, 'utf-8')

  assert.equal(source.includes("appStore.setDataPane('figure')"), true)
  assert.equal(source.includes("appStore.setActiveTab('chart')"), false)
})

test('onboarding copy is consistent about OpenRouter API key setup', () => {
  const chatInputPath = resolve(process.cwd(), 'src/components/chat/ChatInput.vue')
  const chatTabPath = resolve(process.cwd(), 'src/components/chat/ChatTab.vue')
  const apiTabPath = resolve(process.cwd(), 'src/components/modals/ApiTab.vue')

  const chatInput = readFileSync(chatInputPath, 'utf-8')
  const chatTab = readFileSync(chatTabPath, 'utf-8')
  const apiTab = readFileSync(apiTabPath, 'utf-8')

  assert.equal(chatInput.includes('Gemini API key'), false)
  assert.equal(chatTab.includes('Gemini API key'), false)
  assert.equal(chatInput.includes('OpenRouter API key'), true)
  assert.equal(chatTab.includes('OpenRouter API key'), true)
  assert.equal(apiTab.includes('API Key (OpenRouter)'), true)
})
