import test from 'node:test'
import assert from 'node:assert/strict'

import { ensureExecutionTableReady } from '../src/utils/executionTableGuard.js'

function createStore(overrides = {}) {
  const state = {
    ingestedTableName: '',
    schemaFileId: '',
    dataFilePath: '',
    setIngestedTableNameCalls: [],
    setSchemaFileIdCalls: [],
    setDataFilePathCalls: [],
    setIngestedColumnsCalls: []
  }

  return {
    ...state,
    ...overrides,
    setIngestedTableName(value) {
      this.setIngestedTableNameCalls.push(value)
      this.ingestedTableName = value
    },
    setSchemaFileId(value) {
      this.setSchemaFileIdCalls.push(value)
      this.schemaFileId = value
    },
    setDataFilePath(value) {
      this.setDataFilePathCalls.push(value)
      this.dataFilePath = value
    },
    setIngestedColumns(value) {
      this.setIngestedColumnsCalls.push(value)
    }
  }
}

test('ensureExecutionTableReady skips when no dataset is selected', async () => {
  const store = createStore()
  let called = false

  const result = await ensureExecutionTableReady({
    appStore: store,
    ensureTableReady: async () => {
      called = true
      return null
    }
  })

  assert.equal(result, null)
  assert.equal(called, false)
})

test('ensureExecutionTableReady recovers from browser path and syncs state', async () => {
  const store = createStore({
    dataFilePath: 'browser://ball_by_ball_ipl'
  })

  const result = await ensureExecutionTableReady({
    appStore: store,
    duckdb: { getTableNames: async () => [] },
    ensureTableReady: async ({ expectedTableName }) => {
      assert.equal(expectedTableName, 'ball_by_ball_ipl')
      return {
        tableName: 'ball_by_ball_ipl',
        columns: [{ name: 'Batter', type: 'VARCHAR' }]
      }
    }
  })

  assert.equal(result.tableName, 'ball_by_ball_ipl')
  assert.deepEqual(store.setIngestedTableNameCalls, ['ball_by_ball_ipl'])
  assert.deepEqual(store.setSchemaFileIdCalls, ['browser://ball_by_ball_ipl'])
  assert.deepEqual(store.setDataFilePathCalls, ['browser://ball_by_ball_ipl'])
  assert.equal(store.setIngestedColumnsCalls.length, 1)
})
