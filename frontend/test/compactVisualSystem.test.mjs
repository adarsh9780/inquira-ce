import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

function read(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf8')
}

test('shared visual tokens define a compact desktop typography scale', () => {
  const styles = read('src/style.css')

  assert.match(styles, /--text-caption: 0\.6875rem;/)
  assert.match(styles, /--text-ui: 0\.8125rem;/)
  assert.match(styles, /--line-height-ui: 1\.4;/)
  assert.match(styles, /body \{[\s\S]*font-size: var\(--font-size-sm\);[\s\S]*line-height: var\(--line-height-body\);/)
  assert.match(styles, /\.app-toolbar \{[\s\S]*height: 2\.625rem;/)
  assert.match(styles, /\.segmented-control-item \{[\s\S]*height: 1\.75rem;/)
  assert.match(styles, /\.input-base \{[\s\S]*font-size: var\(--text-ui\);/)
})

test('primary navigation and settings use the compact shell metrics', () => {
  const app = read('src/App.vue')
  const sidebar = read('src/components/layout/UnifiedSidebar.vue')
  const settings = read('src/components/modals/SettingsModal.vue')

  assert.match(app, /\.app-nav-pane \{[\s\S]*width: 244px;/)
  assert.match(app, /\.app-nav-pane-collapsed \{\s*width: 52px;/)
  assert.match(sidebar, /\.sidebar-brand-row \{[\s\S]*height: 3rem;/)
  assert.match(sidebar, /\.sidebar-row-label \{[\s\S]*font-weight: 500;/)
  assert.match(settings, /h-\[min\(640px,calc\(100dvh-2rem\)\)\]/)
  assert.match(settings, /w-\[176px\]/)
})

test('brand mark is a crisp animated vector at sidebar scale', () => {
  const sourceMark = read('src/assets/favicon.svg')
  const publicMark = read('public/favicon.svg')

  for (const mark of [sourceMark, publicMark]) {
    assert.match(mark, /viewBox="0 0 32 32"/)
    assert.doesNotMatch(mark, /<filter|feGaussianBlur/)
    assert.match(mark, /shape-rendering="geometricPrecision"/)
    assert.match(mark, /<animateTransform[^>]+type="rotate"[^>]+dur="16s"/)
    assert.match(mark, /stroke-linecap="round"/)
  }
  assert.equal(sourceMark, publicMark)
})
