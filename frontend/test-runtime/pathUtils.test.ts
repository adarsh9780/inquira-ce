import { expect, test } from 'vitest'
import { filenameFromPath } from '../src/utils/pathUtils'

test('filenameFromPath handles posix and Windows paths', () => {
  expect(filenameFromPath('/tmp/report.csv')).toBe('report.csv')
  expect(filenameFromPath('C:\\Users\\me\\Downloads\\report.csv')).toBe('report.csv')
  expect(filenameFromPath('', 'dataset')).toBe('dataset')
})
