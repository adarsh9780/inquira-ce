import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('code tab shows a source toggle after user edits generated code', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/analysis/CodeTab.vue'), 'utf-8')

  assert.equal(source.includes('v-if="showCodeSourceToggle"'), true)
  assert.equal(source.includes('title="Use agent generated code"'), true)
  assert.equal(source.includes('title="Use your edited code"'), true)
  assert.equal(source.includes("@click=\"selectCodeSource('agent')\""), true)
  assert.equal(source.includes("@click=\"selectCodeSource('user')\""), true)
  assert.equal(source.includes('const previousContent = update.startState.doc.toString()'), true)
  assert.equal(source.includes('appStore.noteUserEditedCode(content, { baselineCode: previousContent })'), true)
  assert.equal(source.includes("if (newCode && appStore.codeEditorSource === 'agent' && !appStore.hasUserEditedCode)"), true)
  assert.equal(source.includes('appStore.setCodeEditorSource(source)'), true)
})

test('app store persists edited code source selection separately from generated code', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/stores/appStore.js'), 'utf-8')

  assert.equal(source.includes('const userEditedCode = ref(\'\')'), true)
  assert.equal(source.includes('const hasUserEditedCode = ref(false)'), true)
  assert.equal(source.includes('const codeEditorSource = ref(\'agent\')'), true)
  assert.equal(source.includes('user_edited_code: userEditedCode.value || \'\''), true)
  assert.equal(source.includes('has_user_edited_code: !!hasUserEditedCode.value'), true)
  assert.equal(source.includes('function resolveAgentCodeBaseline(fallbackCode = \'\')'), true)
  assert.equal(source.includes('const activeCode = String(activeTurnCode.value || \'\')'), true)
  assert.equal(source.includes('function noteUserEditedCode(content, options = {})'), true)
  assert.equal(source.includes('const baselineFallback = previousContent && previousContent !== edited ? previousContent : \'\''), true)
  assert.equal(source.includes('function setCodeEditorSource(source)'), true)
  assert.equal(source.includes('pythonFileContent.value = normalized === \'user\''), true)
})
