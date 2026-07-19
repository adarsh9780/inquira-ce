import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const source = fs.readFileSync(path.join(root, 'src/services/apiService.js'), 'utf8')

test('turn-tree mutations use native Wails bindings when available', () => {
  for (const method of [
    'UpdateConversation', 'DeleteConversationTurn', 'MoveConversationTurn',
    'ReorderConversationTurns', 'GetFinalConversationTurn',
    'MarkFinalConversationTurn', 'RerunFinalConversationTurn',
  ]) {
    assert.match(source, new RegExp(`app\\?\\.${method}|app\\.${method}`))
  }
  assert.match(source, /item\.final_turn_id/)
})

test('artifact list, metadata, paging, usage, and delete use native Wails bindings', () => {
  for (const method of [
    'ListWorkspaceArtifacts', 'ListTurnArtifactSummaries',
    'GetWorkspaceArtifactMetadata', 'GetTurnArtifactMetadata',
    'GetWorkspaceArtifactRows', 'GetTurnArtifactRows',
    'GetWorkspaceArtifactUsage', 'DeleteWorkspaceArtifact', 'DeleteTurnArtifact',
  ]) {
    assert.match(source, new RegExp(`app\\?\\.${method}|app\\.${method}`))
  }
})
