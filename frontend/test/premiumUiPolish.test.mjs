import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const read = (path) => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8')

test('premium UI foundation exposes semantic surface, focus, motion, and chart tokens', () => {
  const styles = read('src/style.css')

  for (const token of [
    '--color-surface-raised:',
    '--color-surface-inset:',
    '--color-focus-ring:',
    '--color-chart-paper:',
    '--color-chart-plot:',
    '--color-chart-tooltip-bg:',
    '--color-chart-tooltip-border:',
    '--shadow-composer:',
    '--shadow-overlay:',
    '--motion-duration-entrance:',
    '--motion-ease-spring:',
  ]) {
    assert.equal(styles.includes(token), true, `missing ${token}`)
  }
})

test('workspace shell, composer, and chart surfaces use shared premium primitives', () => {
  const styles = read('src/style.css')
  const app = read('src/App.vue')
  const composer = read('src/components/chat/ChatInput.vue')
  const figure = read('src/components/analysis/FigureTab.vue')
  const runChart = read('src/components/analysis/runs/RunChartOutput.vue')

  assert.match(styles, /\.app-shell-frame\s*\{[\s\S]*animation:\s*shell-reveal/)
  assert.match(styles, /@keyframes shell-reveal/)
  assert.match(styles, /\.chat-composer-surface\s*\{/)
  assert.match(styles, /\.plotly-surface \.modebar/)
  assert.match(styles, /:focus-visible[\s\S]*--color-focus-ring/)
  assert.match(styles, /@media \(prefers-reduced-motion: reduce\)/)

  assert.match(app, /class="flex-1 flex overflow-hidden app-shell-frame relative"/)
  assert.match(composer, /chat-composer-surface/)
  assert.equal(figure.includes('plotly-surface'), true)
  assert.equal(runChart.includes('plotly-surface'), true)
})
