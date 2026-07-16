import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

import {
  layoutTurnTree,
  turnTreeGraphEdgePath,
  turnTreeGraphPort,
  TURN_TREE_GRAPH_NODE_WIDTH,
} from '../src/utils/turnTreeGraphLayout.js'

const graphViewSource = readFileSync(new URL('../src/components/chat/TurnTreeGraphView.vue', import.meta.url), 'utf8')

test('turn tree edge paths connect visible parent and child port centers', () => {
  const layout = layoutTurnTree([
    {
      id: 'root',
      seq_no: 1,
      children: [
        { id: 'branch-a', seq_no: 2, children: [] },
        {
          id: 'branch-b',
          seq_no: 3,
          children: [{ id: 'leaf', seq_no: 4, children: [] }],
        },
      ],
    },
  ])

  for (const edge of layout.edges) {
    const parent = layout.nodes.find((node) => node.id === edge.parentId)
    const child = layout.nodes.find((node) => node.id === edge.childId)
    const output = turnTreeGraphPort(parent, 'output')
    const input = turnTreeGraphPort(child, 'input')
    const path = turnTreeGraphEdgePath(parent, child)

    assert.equal(output.x, parent.x + TURN_TREE_GRAPH_NODE_WIDTH)
    assert.equal(input.x, child.x)
    assert.equal(path.startsWith(`M ${output.x} ${output.y}`), true)
    assert.equal(path.includes(' C '), true)
    assert.equal(path.endsWith(`${input.x} ${input.y}`), true)
  }
})

test('turn tree graph renders synced SVG and HTML layers without foreignObject cards', () => {
  assert.equal(graphViewSource.includes('<foreignObject'), false)
  assert.equal(graphViewSource.includes('data-turn-tree-edge-layer'), true)
  assert.equal(graphViewSource.includes('data-turn-tree-node-layer'), true)
  assert.equal(graphViewSource.includes('data-turn-tree-port-layer'), true)
  assert.equal(graphViewSource.includes(':style="viewportLayerStyle(conversation.id)"'), true)
  assert.equal(graphViewSource.includes('class="turn-tree-node-shell absolute"'), true)
  assert.equal(graphViewSource.includes(':style="nodeStyle(node)"'), true)
  assert.equal(graphViewSource.includes('class="turn-tree-port"'), true)
  assert.equal(graphViewSource.includes('v-if="node.depth > 0"'), true)
  assert.equal(graphViewSource.includes('v-if="node.children?.length"'), true)
  assert.equal(graphViewSource.includes("turnTreeGraphPort(node, 'input')"), true)
  assert.equal(graphViewSource.includes("turnTreeGraphPort(node, 'output')"), true)
  assert.equal(graphViewSource.includes('@wheel.prevent="handleWheel(conversation.id, $event)"'), true)
  assert.equal(graphViewSource.includes(':viewBox="svgViewBox(conversation.id)"'), true)
  assert.equal(graphViewSource.includes('turn-tree-edge-active'), true)
})
