import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat autocomplete accepts suggestions with Tab only, not Enter', () => {
  const componentPath = resolve(process.cwd(), 'src/components/chat/ChatInput.vue')
  const source = readFileSync(componentPath, 'utf-8')

  assert.equal(
    source.includes("if ((showCommandSuggestions.value || showColumnSuggestions.value) && event.key === 'Tab')"),
    true,
  )
  assert.equal(source.includes("event.key === 'Enter' && !event.shiftKey"), false)
})

test('code editor Tab accepts completion before indent and Enter does not accept completion', () => {
  const codeTabPath = resolve(process.cwd(), 'src/components/analysis/CodeTab.vue')
  const source = readFileSync(codeTabPath, 'utf-8')

  assert.equal(source.includes('function acceptCompletionOrIndent(view) {'), true)
  assert.equal(source.includes('if (acceptCompletion(view)) return true'), true)
  assert.equal(source.includes("return indentMore(view)"), true)
  assert.equal(source.includes("{ key: 'Tab', run: acceptCompletionOrIndent }"), true)
  assert.equal(source.includes('function handleEnterWithoutAutocompleteAccept(view) {'), true)
  assert.equal(source.includes('if (completionStatus(view.state)) {'), true)
  assert.equal(source.includes('return insertNewlineAndIndent(view)'), true)
  assert.equal(source.includes("{ key: 'Enter', run: handleEnterWithoutAutocompleteAccept }"), true)
  assert.equal(source.includes("{ key: 'Tab', run: indentMore }"), false)
})
