import test from 'node:test'
import assert from 'node:assert/strict'
import { filenameFromPath } from '../src/utils/pathUtils.js'

test('filenameFromPath handles posix and Windows paths', () => {
  assert.equal(filenameFromPath('/tmp/report.csv'), 'report.csv')
  assert.equal(filenameFromPath('C:\\Users\\me\\Downloads\\report.csv'), 'report.csv')
  assert.equal(filenameFromPath('', 'dataset'), 'dataset')
})
