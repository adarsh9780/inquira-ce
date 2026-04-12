import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app theme uses Ubuntu and the orange brand accent from the public site', () => {
  const styleSource = readFileSync(resolve(process.cwd(), 'src/style.css'), 'utf-8')

  assert.equal(styleSource.includes("family=Ubuntu:ital,wght@0,400;0,500;0,700"), true)
  assert.equal(styleSource.includes("family=Ubuntu+Mono:wght@400;700"), true)
  assert.equal(styleSource.includes('--font-ui: "Ubuntu"'), true)
  assert.equal(styleSource.includes('--font-display: "Ubuntu"'), true)
  assert.equal(styleSource.includes('--font-mono: "Ubuntu Mono", monospace;'), true)
  assert.equal(styleSource.includes('--color-base: #FAF9F6;'), true)
  assert.equal(styleSource.includes('--color-sidebar-surface: #EFEDE8;'), true)
  assert.equal(styleSource.includes('--color-text-main: #1A1F2E;'), true)
  assert.equal(styleSource.includes('--color-text-muted: #6B7280;'), true)
  assert.equal(styleSource.includes('--color-accent: #C96A2E;'), true)
  assert.equal(styleSource.includes('--color-secondary-accent: #5B7FD4;'), true)
  assert.equal(styleSource.includes('--color-accent-text: #8B4C22;'), true)
  assert.equal(styleSource.includes('--color-accent-soft: #F3E8DF;'), true)
  assert.equal(styleSource.includes('--color-primary-900: #C96A2E;'), true)
  assert.equal(styleSource.includes('--color-chat-user-bubble: #F3E8DF;'), true)
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

  assert.equal(splashSource.includes('font-family: "Ubuntu"'), true)
  assert.equal(splashSource.includes('--color-text-main: #1A1F2E;'), true)
  assert.equal(splashSource.includes('--color-accent: #C96A2E;'), true)
  assert.equal(splashSource.includes('background: var(--color-accent);'), true)
})
