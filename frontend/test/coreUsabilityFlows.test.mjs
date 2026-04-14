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
  assert.equal(source.includes('applyExecutionArtifactsToStore(orderedViewModel)'), true)
})

test('chat tab exposes conversation lifecycle controls for usable analysis sessions', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/chat/ChatTab.vue'), 'utf-8')

  assert.equal(source.includes('title="New Conversation"'), true)
  assert.equal(source.includes('title="Clear Conversation"'), true)
  assert.equal(source.includes('title="Delete Conversation"'), false)
  assert.equal(source.includes('await appStore.createConversation()'), true)
  assert.equal(source.includes('await appStore.fetchConversationTurns({ reset: true })'), true)
  assert.equal(source.includes('await appStore.clearActiveConversation()'), true)
  assert.equal(source.includes('await appStore.deleteActiveConversation()'), false)
})

test('critical workflow helper sets up workspace and dataset before higher-level interactions', () => {
  const source = readFileSync(resolve(process.cwd(), 'e2e/support/criticalWorkflow.js'), 'utf-8')

  assert.equal(source.includes('export async function setupCriticalWorkspace(page) {'), true)
  assert.equal(source.includes("await page.getByTitle('Add Dataset').click()"), true)
  assert.equal(source.includes('await importDatasetFromNativePathBridge(page)'), true)
  assert.equal(source.includes('await expect(page.getByText(`Loaded "${datasetFileName}"`)).toBeVisible'), true)
})

test('manual code workflow uses an exact Code tab selector before editing the script', () => {
  const source = readFileSync(resolve(process.cwd(), 'e2e/manual-code-execution.spec.js'), 'utf-8')

  assert.equal(source.includes("getByRole('button', { name: 'Code', exact: true })"), true)
  assert.equal(source.includes("page.getByTitle('Run Code (R)').click()"), true)
})
