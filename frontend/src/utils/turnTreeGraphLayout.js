export const TURN_TREE_GRAPH_NODE_WIDTH = 220
export const TURN_TREE_GRAPH_NODE_HEIGHT = 88
export const TURN_TREE_GRAPH_COLUMN_GAP = 96
export const TURN_TREE_GRAPH_ROW_GAP = 40
export const TURN_TREE_GRAPH_PADDING = 32

export function layoutTurnTree(roots) {
  const nodes = []
  const edges = []
  const seenIds = new Set()
  let nextLeafY = TURN_TREE_GRAPH_PADDING

  function visit(rawNode, depth, ancestors) {
    const id = String(rawNode?.id || '').trim()
    if (!id || seenIds.has(id) || ancestors.has(id)) return null

    seenIds.add(id)
    const nextAncestors = new Set(ancestors)
    nextAncestors.add(id)
    const childLayouts = []
    const children = Array.isArray(rawNode?.children) ? rawNode.children : []

    for (const child of children) {
      const childLayout = visit(child, depth + 1, nextAncestors)
      if (!childLayout) continue
      childLayouts.push(childLayout)
      edges.push({ id: `${id}-${childLayout.id}`, parentId: id, childId: childLayout.id })
    }

    let y
    if (childLayouts.length === 0) {
      y = nextLeafY
      nextLeafY += TURN_TREE_GRAPH_NODE_HEIGHT + TURN_TREE_GRAPH_ROW_GAP
    } else {
      const firstCenter = childLayouts[0].y + (TURN_TREE_GRAPH_NODE_HEIGHT / 2)
      const lastCenter = childLayouts[childLayouts.length - 1].y + (TURN_TREE_GRAPH_NODE_HEIGHT / 2)
      y = ((firstCenter + lastCenter) / 2) - (TURN_TREE_GRAPH_NODE_HEIGHT / 2)
    }

    const node = {
      ...rawNode,
      id,
      x: TURN_TREE_GRAPH_PADDING + (depth * (TURN_TREE_GRAPH_NODE_WIDTH + TURN_TREE_GRAPH_COLUMN_GAP)),
      y,
      depth,
    }
    nodes.push(node)
    return node
  }

  for (const root of Array.isArray(roots) ? roots : []) {
    visit(root, 0, new Set())
  }

  if (nodes.length === 0) {
    return {
      nodes: [],
      edges: [],
      bounds: { x: 0, y: 0, width: 0, height: 0 },
    }
  }

  const maxX = Math.max(...nodes.map((node) => node.x + TURN_TREE_GRAPH_NODE_WIDTH))
  const maxY = Math.max(...nodes.map((node) => node.y + TURN_TREE_GRAPH_NODE_HEIGHT))
  return {
    nodes,
    edges,
    bounds: {
      x: 0,
      y: 0,
      width: maxX + TURN_TREE_GRAPH_PADDING,
      height: maxY + TURN_TREE_GRAPH_PADDING,
    },
  }
}

export function turnTreeGraphEdgePath(parent, child) {
  if (!parent || !child) return ''
  const startX = parent.x + TURN_TREE_GRAPH_NODE_WIDTH
  const startY = parent.y + (TURN_TREE_GRAPH_NODE_HEIGHT / 2)
  const endX = child.x
  const endY = child.y + (TURN_TREE_GRAPH_NODE_HEIGHT / 2)
  const controlOffset = Math.max(36, (endX - startX) / 2)
  return `M ${startX} ${startY} C ${startX + controlOffset} ${startY}, ${endX - controlOffset} ${endY}, ${endX} ${endY}`
}
