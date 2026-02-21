import test from 'node:test'
import assert from 'node:assert/strict'
import { ensureBrowserTableReady } from '../src/utils/browserTableRecovery.js'

test('ensureBrowserTableReady returns fast when table already loaded', async () => {
  const result = await ensureBrowserTableReady({
    expectedTableName: 'ball_by_ball_ipl',
    duckdb: {
      getTableNames: async () => ['ball_by_ball_ipl']
    },
    canPersistHandles: false
  })
  assert.equal(result.recovered, false)
  assert.equal(result.tableName, 'ball_by_ball_ipl')
})

test('ensureBrowserTableReady recovers missing table using saved file handle', async () => {
  const handle = {
    queryPermission: async () => 'granted',
    getFile: async () => ({ name: 'ipl.csv' })
  }
  const result = await ensureBrowserTableReady({
    expectedTableName: 'ball_by_ball_ipl',
    duckdb: {
      getTableNames: async () => [],
      ingestFile: async () => ({
        tableName: 'ball_by_ball_ipl',
        columns: [{ name: 'runs', type: 'INTEGER' }]
      })
    },
    canPersistHandles: true,
    getHandleRecord: async () => ({ handle }),
    clearHandle: async () => true
  })
  assert.equal(result.recovered, true)
  assert.equal(result.tableName, 'ball_by_ball_ipl')
  assert.equal(result.fileName, 'ipl.csv')
  assert.equal(result.columns.length, 1)
})

test('ensureBrowserTableReady throws clear error when no saved handle exists', async () => {
  await assert.rejects(
    () =>
      ensureBrowserTableReady({
        expectedTableName: 'ball_by_ball_ipl',
        duckdb: { getTableNames: async () => [] },
        canPersistHandles: true,
        getHandleRecord: async () => null
      }),
    /No saved data file handle found/
  )
})
