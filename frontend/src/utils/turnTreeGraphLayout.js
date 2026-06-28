export const TURN_TREE_GRAPH_NODE_WIDTH = 220
export const TURN_TREE_GRAPH_NODE_HEIGHT = 88
export const TURN_TREE_GRAPH_COLUMN_GAP = 96
export const TURN_TREE_GRAPH_ROW_GAP = 40
export const TURN_TREE_GRAPH_PADDING = 32
export const TURN_TREE_GRAPH_PORT_RADIUS = 4

export function layoutTurnTree(roots) {
  const nodes = []
  const edges = []
  const seenIds = new Set()
  const displayNumbers = new Map()
  let nextLeafY = TURN_TREE_GRAPH_PADDING

  const visibleNodes = []
  function collectVisibleNodes(rawNodes) {
    for (const rawNode of Array.isArray(rawNodes) ? rawNodes : []) {
      const id = String(rawNode?.id || '').trim()
      if (!id || displayNumbers.has(id)) continue
      visibleNodes.push(rawNode)
      displayNumbers.set(id, 0)
      collectVisibleNodes(rawNode?.children)
    }
  }

  collectVisibleNodes(roots)
  visibleNodes
    .sort((left, right) => (
      Number(left?.seq_no || 0) - Number(right?.seq_no || 0)
      || String(left?.created_at || '').localeCompare(String(right?.created_at || ''))
      || String(left?.id || '').localeCompare(String(right?.id || ''))
    ))
    .forEach((node, index) => displayNumbers.set(String(node?.id || '').trim(), index + 1))

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
      display_no: displayNumbers.get(id),
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
  const { x: startX, y: startY } = turnTreeGraphPort(parent, 'output')
  const { x: endX, y: endY } = turnTreeGraphPort(child, 'input')
  const deltaX = endX - startX
  const deltaY = endY - startY
  const midX = startX + (deltaX / 2)
  const midY = startY + (deltaY / 2)
  const waveDirection = deltaY < 0 ? -1 : 1
  const wave = clamp(Math.abs(deltaY) * 0.18, 8, 24) * waveDirection
  return [
    `M ${startX} ${startY}`,
    `C ${startX + (deltaX * 0.28)} ${startY + wave} ${midX - (deltaX * 0.12)} ${midY - wave} ${midX} ${midY}`,
    `C ${midX + (deltaX * 0.12)} ${midY + wave} ${endX - (deltaX * 0.28)} ${endY - wave} ${endX} ${endY}`,
  ].join(' ')
}

export function turnTreeGraphPort(node, side) {
  if (!node) return { x: 0, y: 0 }
  return {
    x: side === 'output' ? node.x + TURN_TREE_GRAPH_NODE_WIDTH : node.x,
    y: node.y + (TURN_TREE_GRAPH_NODE_HEIGHT / 2),
  }
}

function clamp(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, value))
}
