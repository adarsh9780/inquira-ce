import { describe, expect, it } from 'vitest'

import {
  layoutTurnTree,
  turnTreeGraphEdgePath,
  TURN_TREE_GRAPH_NODE_HEIGHT,
} from '../src/utils/turnTreeGraphLayout'

describe('turn tree graph layout', () => {
  it('lays out linear trees from left to right', () => {
    const layout = layoutTurnTree([{ id: 'root', children: [{ id: 'child', children: [{ id: 'leaf' }] }] }])
    const [leaf, child, root] = layout.nodes

    expect(root.x).toBeLessThan(child.x)
    expect(child.x).toBeLessThan(leaf.x)
    expect(new Set(layout.nodes.map((node) => node.y)).size).toBe(1)
    expect(layout.edges).toHaveLength(2)
  })

  it('centers parents and assigns distinct leaf rows across branches and roots', () => {
    const layout = layoutTurnTree([
      { id: 'root', children: [{ id: 'left' }, { id: 'right' }] },
      { id: 'second-root' },
    ])
    const byId = Object.fromEntries(layout.nodes.map((node) => [node.id, node]))
    const expectedRootY = ((byId.left.y + byId.right.y + TURN_TREE_GRAPH_NODE_HEIGHT) / 2) - (TURN_TREE_GRAPH_NODE_HEIGHT / 2)

    expect(byId.root.y).toBe(expectedRootY)
    expect(new Set([byId.left.y, byId.right.y, byId['second-root'].y]).size).toBe(3)
  })

  it('ignores malformed, duplicate, and cyclic nodes without failing', () => {
    const root = { id: 'root', children: [] }
    root.children.push({ id: '' }, { id: 'root' }, root, { id: 'valid', children: 'invalid' })
    const layout = layoutTurnTree([null, root, { id: 'valid' }])

    expect(layout.nodes.map((node) => node.id).sort()).toEqual(['root', 'valid'])
    expect(layout.edges).toHaveLength(1)
    expect(turnTreeGraphEdgePath(layout.nodes[1], layout.nodes[0])).toContain(' H ')
  })

  it('assigns contiguous display numbers when stored sequence numbers have gaps', () => {
    const layout = layoutTurnTree([
      { id: 'turn-1', seq_no: 1, children: [{ id: 'turn-4', seq_no: 4 }] },
      { id: 'turn-6', seq_no: 6 },
    ])
    const byId = Object.fromEntries(layout.nodes.map((node) => [node.id, node]))

    expect(byId['turn-1'].display_no).toBe(1)
    expect(byId['turn-4'].display_no).toBe(2)
    expect(byId['turn-6'].display_no).toBe(3)
  })

  it('draws connected elbow edges from the parent boundary to the child boundary', () => {
    const parent = { x: 10, y: 20 }
    const child = { x: 400, y: 140 }
    const path = turnTreeGraphEdgePath(parent, child)

    expect(path.startsWith('M 230 64')).toBe(true)
    expect(path.endsWith('H 400')).toBe(true)
  })

  it('returns empty bounds for an empty tree', () => {
    expect(layoutTurnTree([])).toEqual({
      nodes: [],
      edges: [],
      bounds: { x: 0, y: 0, width: 0, height: 0 },
    })
  })
})
