import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

const source = readFileSync(
  resolve(process.cwd(), 'src/components/modals/tabs/WorkspaceTab.vue'),
  'utf8',
)

test('workspace settings imports the path formatter used while rendering project cards', () => {
  assert.match(
    source,
    /import \{ filenameFromPath \} from '\.\.\/\.\.\/\.\.\/utils\/pathUtils'/,
  )
  assert.match(source, /const filename = filenameFromPath\(duckdbPath, 'workspace\.duckdb'\)/)
})

test('active workspace lookup tolerates a failed project-card computation', () => {
  assert.match(
    source,
    /const cards = Array\.isArray\(workspaceCards\.value\) \? workspaceCards\.value : \[\]/,
  )
  assert.match(source, /return cards\.find\(/)
})
