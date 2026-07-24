import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('markdown code fences render editor-like block with copy icon and delegated copy handler', () => {
  const chatHistoryPath = resolve(process.cwd(), 'src/components/chat/ChatHistory.vue')
  const history = readFileSync(chatHistoryPath, 'utf-8')
  const renderer = readFileSync(resolve(process.cwd(), 'src/utils/messageRendering.ts'), 'utf-8')
  const markdownContent = readFileSync(resolve(process.cwd(), 'src/components/chat/MarkdownContent.vue'), 'utf-8')
  const source = [history, renderer, markdownContent].join('\n')

  assert.equal(source.includes("import Prism from 'prismjs'"), true)
  assert.equal(source.includes("import 'prismjs/components/prism-python'"), true)
  assert.equal(source.includes("import 'prismjs/components/prism-sql'"), true)
  assert.equal(source.includes('class="chat-code-copy"'), true)
  assert.equal(source.includes('aria-label="Copy code"'), true)
  assert.equal(source.includes("container.addEventListener('click', handleChatContainerClick)"), true)
  assert.equal(source.includes('void copyCodeFromBlock(copyButton)'), true)
  assert.equal(source.includes('const language = resolveLanguage'), true)
  assert.equal(source.includes('Prism.highlight(rawCode, grammar, language)'), true)
  assert.equal(source.includes("'duckdb'"), true)
  assert.equal(source.includes("? 'sql' : 'python'"), true)
  assert.equal(source.includes('export function renderCode(content: unknown)'), true)
  assert.equal(source.includes("Prism.highlight(rawCode, grammar, 'python')"), true)
  assert.equal(source.includes('class="language-python" v-html="rendered"'), true)
  assert.equal(source.includes(':deep(.chat-code-block)'), true)
  assert.equal(source.includes('background-color: var(--color-base);'), true)
  assert.equal(source.includes('background-color: var(--color-surface);'), true)
})
