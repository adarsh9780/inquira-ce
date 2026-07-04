import test from 'node:test'
import assert from 'node:assert/strict'
import { workspaceInitials } from '../src/utils/workspaceDisplay.js'

test('workspace initials produce compact collapsed-sidebar labels', () => {
  assert.equal(workspaceInitials('Revenue Analytics'), 'RA')
  assert.equal(workspaceInitials('sales_ops'), 'SO')
  assert.equal(workspaceInitials('warehouse'), 'WA')
  assert.equal(workspaceInitials(''), 'WS')
})
