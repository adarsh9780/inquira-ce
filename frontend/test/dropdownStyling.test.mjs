import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('dropdowns in FigureTab and TableTab use small font and grey color styling', () => {
    const figureTabPath = resolve(process.cwd(), 'src/components/analysis/FigureTab.vue')
    const tableTabPath = resolve(process.cwd(), 'src/components/analysis/TableTab.vue')

    const figureTab = readFileSync(figureTabPath, 'utf-8')
    const tableTab = readFileSync(tableTabPath, 'utf-8')

    // Check that select uses text-xs and the defined styles for colors
    const expectedClasses = 'text-xs'
    const expectedStyles = 'color: var(--color-text-muted)'

    assert.equal(figureTab.includes('<select'), true)
    assert.equal(tableTab.includes('<select'), true)

    assert.equal(figureTab.includes(expectedClasses), true)
    assert.equal(figureTab.includes(expectedStyles), true)

    assert.equal(tableTab.includes(expectedClasses), true)
    assert.equal(tableTab.includes(expectedStyles), true)
})
