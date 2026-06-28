import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('analysis panels use short action-oriented empty states', () => {
  const tableSource = readFileSync(resolve(process.cwd(), 'src/components/analysis/TableTab.vue'), 'utf-8')
  const figureSource = readFileSync(resolve(process.cwd(), 'src/components/analysis/FigureTab.vue'), 'utf-8')
  const outputSource = readFileSync(resolve(process.cwd(), 'src/components/analysis/OutputTab.vue'), 'utf-8')
  const treeSource = readFileSync(resolve(process.cwd(), 'src/components/chat/TurnTreeGraphView.vue'), 'utf-8')

  assert.equal(tableSource.includes('title="No saved tables"'), true)
  assert.equal(tableSource.includes('subtitle="Run code that creates a dataframe."'), true)
  assert.equal(figureSource.includes('No saved charts'), true)
  assert.equal(figureSource.includes('Run code that creates a Plotly figure.'), true)
  assert.equal(outputSource.includes('No output yet'), true)
  assert.equal(outputSource.includes('Run code to see logs, errors, tables, and charts.'), true)
  assert.equal(treeSource.includes('Ask a question in Chat to build this tree.'), true)
})
