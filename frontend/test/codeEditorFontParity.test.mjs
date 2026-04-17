import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('code editor uses JetBrains Mono Nerd Font stack', () => {
  const codeTabSource = readFileSync(resolve(process.cwd(), 'src/components/analysis/CodeTab.vue'), 'utf-8')
  const styleSource = readFileSync(resolve(process.cwd(), 'src/style.css'), 'utf-8')

  assert.equal(codeTabSource.includes("'.cm-scroller': { fontFamily: '\"JetBrainsMono Nerd Font\", \"JetBrains Mono\", monospace', backgroundColor: '#FFFFFF' }"), true)
  assert.equal(codeTabSource.includes('Monaco, Menlo, "Ubuntu Mono", monospace'), false)
  assert.equal(codeTabSource.includes("fontFamily: 'var(--font-ui)'"), false)
  assert.equal(styleSource.includes('family=JetBrains+Mono:wght@400;500;700'), true)
})
