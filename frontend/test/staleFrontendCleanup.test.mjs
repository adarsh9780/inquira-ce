import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('top toolbar does not keep unused focusCodeEditor helper after shortcuts cleanup', () => {
  const toolbarPath = resolve(process.cwd(), 'src/components/layout/TopToolbar.vue')
  const source = readFileSync(toolbarPath, 'utf-8')

  assert.equal(source.includes('function focusCodeEditor()'), false)
})

test('api service no longer exposes legacy analyzeData shims that only throw', () => {
  const apiServicePath = resolve(process.cwd(), 'src/services/apiService.js')
  const source = readFileSync(apiServicePath, 'utf-8')

  assert.equal(source.includes('async analyzeData(data, signal = null)'), false)
  assert.equal(source.includes('async analyzeDataStream(data, { signal = null, onEvent = null } = {})'), false)
})

test('execution service no longer includes unused initialize/restoreState no-op methods', () => {
  const executionServicePath = resolve(process.cwd(), 'src/services/executionService.js')
  const source = readFileSync(executionServicePath, 'utf-8')

  assert.equal(source.includes('async initialize(_opts)'), false)
  assert.equal(source.includes('async restoreState(_codeBlocks)'), false)
})
