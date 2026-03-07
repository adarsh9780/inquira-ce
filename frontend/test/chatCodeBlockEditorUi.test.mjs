import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('markdown code fences render editor-like block with copy icon and delegated copy handler', () => {
  const chatHistoryPath = resolve(process.cwd(), 'src/components/chat/ChatHistory.vue')
  const source = readFileSync(chatHistoryPath, 'utf-8')

  assert.equal(source.includes("import Prism from 'prismjs'"), true)
  assert.equal(source.includes("import 'prismjs/components/prism-python'"), true)
  assert.equal(source.includes("import 'prismjs/components/prism-sql'"), true)
  assert.equal(source.includes('class="chat-code-copy"'), true)
  assert.equal(source.includes('aria-label="Copy code"'), true)
  assert.equal(source.includes("container.addEventListener('click', handleChatContainerClick)"), true)
  assert.equal(source.includes('void copyCodeFromBlock(copyButton)'), true)
  assert.equal(source.includes('const prismLanguage = resolvePrismLanguage(requestedLanguage)'), true)
  assert.equal(source.includes('Prism.highlight(rawCode, grammar, prismLanguage)'), true)
  assert.equal(source.includes("normalized === 'duckdb'"), true)
  assert.equal(source.includes("return 'sql'"), true)
  assert.equal(source.includes(':deep(.chat-code-block)'), true)
  assert.equal(source.includes('background-color: #fdfcfb;'), true)
  assert.equal(source.includes('background-color: #f3f3ed;'), true)
})
