import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app theme uses Manrope with semantic theme surfaces and restrained warm brand accents', () => {
  const styleSource = readFileSync(resolve(process.cwd(), 'src/style.css'), 'utf-8')

  assert.equal(styleSource.includes("family=Manrope:wght@400;500;600;700;800"), true)
  assert.equal(styleSource.includes('--font-ui: "Manrope", "Avenir Next", "Segoe UI", sans-serif;'), true)
  assert.equal(styleSource.includes('--font-display: "Manrope", "Avenir Next", "Segoe UI", sans-serif;'), true)
  assert.equal(styleSource.includes('--font-mono: "JetBrainsMono Nerd Font", "JetBrains Mono", monospace;'), true)
  assert.equal(styleSource.includes('--color-base: #FBF8F2;'), true)
  assert.equal(styleSource.includes('--color-sidebar-surface: #ECE6DD;'), true)
  assert.equal(styleSource.includes('--color-text-main: #1E2430;'), true)
  assert.equal(styleSource.includes('--color-text-muted: #6D726F;'), true)
  assert.equal(styleSource.includes('--color-accent: #B86A3D;'), true)
  assert.equal(styleSource.includes('--color-secondary-accent: #4F6FAF;'), true)
  assert.equal(styleSource.includes('--color-accent-text: #7A4729;'), true)
  assert.equal(styleSource.includes('--color-accent-soft: #F2E5D9;'), true)
  assert.equal(styleSource.includes('--color-primary-900: #B86A3D;'), true)
  assert.equal(styleSource.includes('--color-panel-elevated: #FFFDF8;'), true)
  assert.equal(styleSource.includes('--color-selected-surface: #F5E7DB;'), true)
})

test('desktop favicon follows the blue-orange Inquira brand mark', () => {
  const appIconSource = readFileSync(resolve(process.cwd(), 'src/assets/favicon.svg'), 'utf-8')
  const publicIconSource = readFileSync(resolve(process.cwd(), 'public/favicon.svg'), 'utf-8')

  for (const source of [appIconSource, publicIconSource]) {
    assert.equal(source.includes('stop-color:#3b82f6'), true)
    assert.equal(source.includes('stop-color:#f97316'), true)
    assert.equal(source.includes('fill="#8b5cf6"'), false)
    assert.equal(source.includes('fill="#6366f1"'), false)
  }
})

test('native splash screen mirrors the branded font and accent', () => {
  const splashSource = readFileSync(resolve(process.cwd(), 'public/splash.html'), 'utf-8')

  assert.equal(splashSource.includes('font-family: "Manrope"'), true)
  assert.equal(splashSource.includes('--color-text-main: #1E2430;'), true)
  assert.equal(splashSource.includes('--color-accent: #B86A3D;'), true)
  assert.equal(splashSource.includes('background: var(--color-accent);'), true)
})
