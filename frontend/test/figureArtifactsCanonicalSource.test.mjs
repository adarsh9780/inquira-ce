import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('FigureTab uses workspace artifact catalog as canonical source and resolves selected chart by artifact id', () => {
  const figureTabPath = resolve(process.cwd(), 'src/components/analysis/FigureTab.vue')
  const source = readFileSync(figureTabPath, 'utf-8')

  assert.equal(source.includes('const workspaceFigureArtifacts = ref([])'), true)
  assert.equal(source.includes('apiService.v1ListWorkspaceArtifacts('), true)
  assert.equal(source.includes("'figure',"), true)
  assert.equal(source.includes('value: fig.artifact_id,'), true)
  assert.equal(source.includes('appStore.setFigureCount(artifacts.length)'), true)
  assert.equal(source.includes('apiService.v1GetWorkspaceArtifactMetadata('), true)
  assert.equal(source.includes(':key="selectedArtifactId"'), true)
})

test('apiService exposes workspace artifact metadata route used by FigureTab', () => {
  const apiServicePath = resolve(process.cwd(), 'src/services/apiService.js')
  const source = readFileSync(apiServicePath, 'utf-8')

  assert.equal(source.includes('async v1GetWorkspaceArtifactMetadata(workspaceId, artifactId, options = {})'), true)
  assert.equal(source.includes('/api/v1/workspaces/${workspaceId}/artifacts/${artifactId}'), true)
  assert.equal(source.includes('Artifact metadata fetch failed'), true)
})
