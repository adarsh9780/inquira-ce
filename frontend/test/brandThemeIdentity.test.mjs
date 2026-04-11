import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app theme uses Ubuntu and the orange brand accent from the public site', () => {
  const styleSource = readFileSync(resolve(process.cwd(), 'src/style.css'), 'utf-8')

  assert.equal(styleSource.includes('--font-ui: "Ubuntu"'), true)
  assert.equal(styleSource.includes('--font-display: "Ubuntu"'), true)
  assert.equal(styleSource.includes('--color-base: #FFFEFC;'), true)
  assert.equal(styleSource.includes('--color-text-main: #18181B;'), true)
  assert.equal(styleSource.includes('--color-text-muted: #52525B;'), true)
  assert.equal(styleSource.includes('--color-accent: #D47948;'), true)
  assert.equal(styleSource.includes('--color-accent-text: #7C2D12;'), true)
  assert.equal(styleSource.includes('--color-accent-soft: #FFF7ED;'), true)
  assert.equal(styleSource.includes('--color-primary-900: #D47948;'), true)
  assert.equal(styleSource.includes('--color-chat-user-bubble: #FFF7ED;'), true)
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
  assert.equal(splashSource.includes('--color-accent: #D47948;'), true)
  assert.equal(splashSource.includes('background: var(--color-accent);'), true)
})
