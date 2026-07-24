import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

const read = (path) => readFileSync(resolve(process.cwd(), path), 'utf8')

test('chart renderers use the cartesian Plotly distribution', () => {
  const packageJson = JSON.parse(read('package.json'))
  const figureTab = read('src/components/analysis/FigureTab.vue')
  const runChart = read('src/components/analysis/runs/RunChartOutput.vue')
  const viteConfig = read('vite.config.js')

  assert.equal(Boolean(packageJson.dependencies['plotly.js-cartesian-dist-min']), true)
  assert.equal(Boolean(packageJson.dependencies['plotly.js-dist-min']), false)
  assert.match(figureTab, /from 'plotly\.js-cartesian-dist-min'/)
  assert.match(runChart, /from 'plotly\.js-cartesian-dist-min'/)
  assert.match(viteConfig, /node_modules\/plotly\.js-cartesian-dist-min\//)
})

test('the selected Plotly distribution covers the supported analysis trace set', () => {
  const readme = read('node_modules/plotly.js-cartesian-dist-min/README.md')
  for (const trace of ['bar', 'box', 'contour', 'heatmap', 'histogram', 'image', 'pie', 'scatter', 'violin']) {
    assert.match(readme, new RegExp(`\\b${trace}\\b`))
  }
})
