import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('code editor uses JetBrains font stack with design tokens for editor colors', () => {
  const codeTabSource = readFileSync(resolve(process.cwd(), 'src/components/analysis/CodeTab.vue'), 'utf-8')
  const styleSource = readFileSync(resolve(process.cwd(), 'src/style.css'), 'utf-8')

  assert.equal(codeTabSource.includes("'.cm-editor': { backgroundColor: 'var(--color-base)' }"), true)
  assert.equal(codeTabSource.includes("const editorMonoFont = readEditorMonoFont()"), true)
  assert.equal(codeTabSource.includes("getPropertyValue('--font-mono')"), true)
  assert.equal(codeTabSource.includes('const visualThemeCompartment = new Compartment()'), true)
  assert.equal(codeTabSource.includes('effects: visualThemeCompartment.reconfigure(buildEditorThemeExtension())'), true)
  assert.equal(codeTabSource.includes('watch(() => appStore.uiCodeFont, () => {'), true)
  assert.equal(codeTabSource.includes("'.cm-scroller': { fontFamily: editorMonoFont, backgroundColor: 'var(--color-base)' }"), true)
  assert.equal(codeTabSource.includes("backgroundColor: 'var(--color-surface)'"), true)
  assert.equal(codeTabSource.includes("borderRight: '1px solid var(--color-border)'"), true)
  assert.equal(codeTabSource.includes("color: 'var(--color-text-muted)'"), true)
  assert.equal(codeTabSource.includes('Monaco, Menlo, "Ubuntu Mono", monospace'), false)
  assert.equal(codeTabSource.includes("fontFamily: 'var(--font-ui)'"), false)
  assert.equal(codeTabSource.includes('#FFFFFF'), false)
  assert.equal(codeTabSource.includes('#F5F3ED'), false)
  assert.equal(codeTabSource.includes('#E8E4DC'), false)
  assert.equal(codeTabSource.includes('#8a8070'), false)
  assert.equal(codeTabSource.includes('color-mix(in srgb, var(--color-surface) 92%, white)'), false)
  assert.equal(codeTabSource.includes('hover:bg-white'), false)
  assert.equal(codeTabSource.includes('hover:text-green-600'), false)
  assert.equal(styleSource.includes('family=JetBrains+Mono:wght@400;500;700'), true)
  assert.equal(styleSource.includes('--font-mono: "JetBrainsMono Nerd Font", "JetBrains Mono", monospace;'), true)
})
