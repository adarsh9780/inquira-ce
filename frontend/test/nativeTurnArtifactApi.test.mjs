import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const source = [
  'src/api/conversations.ts',
  'src/api/artifacts.ts',
].map((file) => fs.readFileSync(path.join(root, file), 'utf8')).join('\n')

test('supported turn-tree mutations use native Wails bindings', () => {
  for (const method of [
    'UpdateConversation', 'DeleteConversationTurn', 'GetFinalConversationTurn',
    'MarkFinalConversationTurn',
  ]) {
    assert.match(source, new RegExp(`['\"]${method}['\"]`))
  }
  assert.match(source, /item\.final_turn_id/)
})

test('active turn artifacts, paging, usage, and deletion use native Wails bindings', () => {
  for (const method of [
    'ListTurnArtifactSummaries', 'GetTurnArtifactMetadata',
    'GetWorkspaceArtifactRows', 'GetTurnArtifactRows',
    'DeleteTurnArtifact',
  ]) {
    assert.match(source, new RegExp(`['\"]${method}['\"]`))
  }
})
