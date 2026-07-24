import { expect, test } from 'vitest'
import { workspaceInitials } from '../src/utils/workspaceDisplay'

test('workspace initials produce compact collapsed-sidebar labels', () => {
  expect(workspaceInitials('Revenue Analytics')).toBe('RA')
  expect(workspaceInitials('sales_ops')).toBe('SO')
  expect(workspaceInitials('warehouse')).toBe('WA')
  expect(workspaceInitials('')).toBe('WS')
})
