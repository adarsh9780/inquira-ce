import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('terminal tab uses inline prompt input with terminal-like caret styling', () => {
  const terminalPath = resolve(process.cwd(), 'src/components/analysis/TerminalTab.vue')
  const source = readFileSync(terminalPath, 'utf-8')

  assert.equal(source.includes('style="background-color: var(--color-base); color: var(--color-text-main);"'), true)
  assert.equal(source.includes('class="w-full bg-transparent outline-none placeholder:text-slate-400"'), true)
  assert.equal(source.includes('caret-color: var(--color-accent);'), true)
  assert.equal(source.includes('bg-[#0b1228]'), false)
  assert.equal(source.includes('{{ promptPrefix }}'), true)
  assert.equal(source.includes('@click="focusCommandInput"'), true)
})

test('terminal tab supports arrow-key command history navigation', () => {
  const terminalPath = resolve(process.cwd(), 'src/components/analysis/TerminalTab.vue')
  const source = readFileSync(terminalPath, 'utf-8')

  assert.equal(source.includes("if (event.key === 'ArrowUp')"), true)
  assert.equal(source.includes("if (event.key === 'ArrowDown')"), true)
  assert.equal(source.includes('commandHistory.value.push(raw)'), true)
})
