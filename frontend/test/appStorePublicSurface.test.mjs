import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app store public surface excludes retired APIs and keeps supported workflow actions', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/stores/appStore.js'), 'utf-8')
  const publicSurface = source.slice(source.lastIndexOf('  return {'), source.lastIndexOf('\n  }\n})'))

  const retiredMembers = [
    'clearLocalConfig',
    'foregroundOperation',
    'turnViewEnabled',
    'turnsNextCursor',
    'dataFilePath',
    'ingestedTableName',
    'ingestedColumns',
    'hasDataFile',
    'schemaFilePath',
    'schemaFileId',
    'isSchemaFileUploaded',
    'profileData',
    'historicalCodeBlocks',
    'currentExplanation',
    'activeTurnArtifacts',
    'activeTurnTree',
    'workspaceAIConfigLoading',
    'terminalEnabled',
    'selectedResultId',
    'plotlyThemeMode',
    'setSchemaFilePath',
    'setIsSchemaFileUploaded',
    'handleDatasetRemoved',
    'setLlmProvider',
    'ensureWorkspaceRuntimeReady',
    'refreshActiveTurnArtifacts',
    'loadActiveTurn',
    'setTurnViewEnabled',
    'startForegroundOperation',
    'toggleChatOverlay',
    'addHistoricalCodeBlock',
  ]
  const supportedActions = [
    'schemaContext',
    'terminalConsentGranted',
    'fetchWorkspaces',
    'fetchActiveWorkspaceSummary',
    'applyPreferencesResponse',
    'createWorkspace',
    'fetchColumnCatalog',
    'startBackgroundOperation',
    'finishBackgroundOperation',
    'loadActiveTurnRelations',
  ]

  for (const member of retiredMembers) {
    assert.doesNotMatch(publicSurface, new RegExp(`^\\s*${member},?$`, 'm'))
  }
  for (const action of supportedActions) {
    assert.match(publicSurface, new RegExp(`^\\s*${action},?$`, 'm'))
  }
})
