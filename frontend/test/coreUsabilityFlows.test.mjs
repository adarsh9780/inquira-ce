import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('code tab runs manual code through execution service and surfaces output in the results pane', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/analysis/CodeTab.vue'), 'utf-8')

  assert.equal(source.includes('async function runCode() {'), true)
  assert.equal(source.includes('await executeSnippet(appStore.pythonFileContent, \'Code executed successfully!\''), true)
  assert.equal(source.includes("appStore.setActiveTab('output')"), true)
  assert.equal(source.includes("appStore.setTerminalOutput('Running code...')"), true)
  assert.equal(source.includes('const pyResponse = await executionService.executePython(code)'), true)
  assert.equal(source.includes('tableOutputs = stampRunResults(viewModel.dataframes.slice(0, 1)'), true)
  assert.equal(source.includes('chartOutputs = stampRunResults(viewModel.figures.slice(0, 1)'), true)
  assert.equal(source.includes("origin: 'user'"), true)
  assert.equal(source.includes("appStore.setDataPane('output')"), true)
  assert.equal(source.includes('applyExecutionArtifactsToStore'), false)
})

test('chat tab relies on sidebar lifecycle controls for usable analysis sessions', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/chat/ChatTab.vue'), 'utf-8')

  assert.equal(source.includes('title="New Conversation"'), false)
  assert.equal(source.includes('PlusIcon'), false)
  assert.equal(source.includes('title="Clear Conversation"'), false)
  assert.equal(source.includes('title="Delete Conversation"'), false)
  assert.equal(source.includes('await appStore.createConversation()'), false)
  assert.equal(source.includes('await appStore.fetchConversationTurns()'), true)
  assert.equal(source.includes('await appStore.clearActiveConversation()'), false)
  assert.equal(source.includes('await appStore.deleteActiveConversation()'), false)
})
