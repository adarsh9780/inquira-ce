import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'

import TurnTreeGraphView from '../src/components/chat/TurnTreeGraphView.vue'

const conversations = [
  {
    id: 'conversation-1',
    title: 'First',
    final_turn_id: 'turn-2',
    roots: [{ id: 'turn-1', seq_no: 1, user_text: 'Question one', assistant_text: 'Answer one', children: [{ id: 'turn-2', seq_no: 2, user_text: 'Question two', assistant_text: 'Answer two' }] }],
  },
  {
    id: 'conversation-2',
    title: 'Second',
    roots: [{ id: 'turn-3', seq_no: 3, user_text: 'Question three', assistant_text: '' }],
  },
]

describe('TurnTreeGraphView', () => {
  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('renders separate accessible graphs and emits node selections', async () => {
    const wrapper = mount(TurnTreeGraphView, {
      props: { conversations, currentTurnId: 'turn-2', currentParentTurnId: 'turn-1', variant: 'page' },
    })

    expect(wrapper.findAll('[data-turn-tree-graph]')).toHaveLength(2)
    expect(wrapper.findAll('svg[role="img"]')).toHaveLength(2)
    expect(wrapper.get('svg').attributes('viewBox')).toMatch(/^0 0 /)
    expect(wrapper.findAll('.turn-tree-edge-active')).toHaveLength(1)
    expect(wrapper.text()).toContain('Final')
    expect(wrapper.findAll('button[aria-label^="Open turn"]')).toHaveLength(3)

    await wrapper.get('button[aria-label="Open turn 2"]').trigger('click')
    expect(wrapper.emitted('select')).toEqual([[{ conversationId: 'conversation-1', turnId: 'turn-2' }]])
  })

  it('opens shared actions from the visible node menu and emits actions', async () => {
    const wrapper = mount(TurnTreeGraphView, { props: { conversations } })

    await wrapper.get('button[aria-label="Actions for turn 1"]').trigger('click', { clientX: 20, clientY: 30 })
    expect(document.body.textContent).toContain('Mark Final')

    const markFinal = Array.from(document.body.querySelectorAll('[data-turn-tree-context-menu] button'))
      .find((button) => button.textContent.trim() === 'Mark Final')
    markFinal.click()
    await wrapper.vm.$nextTick()
    expect(wrapper.emitted('mark-final')).toEqual([[{ conversationId: 'conversation-1', turnId: 'turn-1' }]])
  })

  it('opens shared actions when a node is right-clicked', async () => {
    const wrapper = mount(TurnTreeGraphView, { props: { conversations } })

    await wrapper.get('button[aria-label="Open turn 2"]').trigger('contextmenu', { clientX: 40, clientY: 50 })

    const menu = document.body.querySelector('[data-turn-tree-context-menu]')
    expect(menu).toBeTruthy()
    expect(menu.getAttribute('style')).toContain('left: 40px')
  })

  it('provides zoom and reset controls with clamped zoom behavior', async () => {
    const wrapper = mount(TurnTreeGraphView, { props: { conversations: [conversations[0]] } })
    const graph = wrapper.get('[data-turn-tree-graph="conversation-1"]').element
    Object.defineProperty(graph, 'clientWidth', { value: 600 })
    Object.defineProperty(graph, 'clientHeight', { value: 360 })
    graph.getBoundingClientRect = () => ({ left: 0, top: 0, width: 600, height: 360 })

    for (let index = 0; index < 30; index += 1) await wrapper.get('button[aria-label="Zoom out"]').trigger('click')
    expect(wrapper.get('svg g').attributes('transform')).toContain('scale(0.35)')

    await wrapper.get('button[aria-label="Reset graph view"]').trigger('click')
    expect(wrapper.get('svg g').attributes('transform')).not.toContain('scale(0.35)')
  })

  it('zooms from the full canvas even when the pointer is over a node card', async () => {
    const wrapper = mount(TurnTreeGraphView, { props: { conversations: [conversations[0]] } })
    const graph = wrapper.get('[data-turn-tree-graph="conversation-1"]').element
    graph.getBoundingClientRect = () => ({ left: 0, top: 0, width: 600, height: 360 })
    const before = wrapper.get('svg g').attributes('transform')

    await wrapper.get('button[aria-label="Open turn 1"]').trigger('wheel', {
      deltaY: -100,
      clientX: 100,
      clientY: 100,
    })

    expect(wrapper.get('svg g').attributes('transform')).not.toBe(before)
  })

  it('keeps edge, node, and port layers on the same viewport transform', async () => {
    const wrapper = mount(TurnTreeGraphView, { props: { conversations: [conversations[0]] } })
    const graph = wrapper.get('[data-turn-tree-graph="conversation-1"]').element
    Object.defineProperty(graph, 'clientWidth', { value: 600 })
    Object.defineProperty(graph, 'clientHeight', { value: 360 })
    graph.getBoundingClientRect = () => ({ left: 0, top: 0, width: 600, height: 360 })

    await wrapper.get('button[aria-label="Reset graph view"]').trigger('click')
    await wrapper.get('button[aria-label="Zoom in"]').trigger('click')

    const edgeTransform = wrapper.get('[data-turn-tree-edge-layer] g').attributes('transform')
    const portTransform = wrapper.get('[data-turn-tree-port-layer] g').attributes('transform')
    const nodeLayerStyle = wrapper.get('[data-turn-tree-node-layer]').attributes('style')
    const match = edgeTransform.match(/^translate\(([-\d.]+) ([-\d.]+)\) scale\(([-\d.]+)\)$/)

    expect(portTransform).toBe(edgeTransform)
    expect(match).toBeTruthy()
    expect(nodeLayerStyle).toContain(`translate(${match[1]}px, ${match[2]}px) scale(${match[3]})`)
  })

  it('collapses and expands each conversation from its header', async () => {
    const wrapper = mount(TurnTreeGraphView, { props: { conversations: [conversations[0]] } })
    await wrapper.vm.$nextTick()
    const header = wrapper.get('button[aria-controls="conversation-graph-conversation-1"]')

    expect(header.attributes('aria-expanded')).toBe('true')
    expect(wrapper.get('[data-turn-tree-graph="conversation-1"]').isVisible()).toBe(true)

    await header.trigger('click')
    expect(header.attributes('aria-expanded')).toBe('false')
    expect(wrapper.get('[data-turn-tree-graph="conversation-1"]').attributes('style')).toContain('display: none')
  })

  it('shows contiguous visible turn numbers when persisted sequence numbers have gaps', () => {
    const wrapper = mount(TurnTreeGraphView, {
      props: {
        conversations: [{
          id: 'conversation-gaps',
          roots: [{ id: 'turn-1', seq_no: 1, children: [{ id: 'turn-4', seq_no: 4 }, { id: 'turn-6', seq_no: 6 }] }],
        }],
      },
    })

    expect(wrapper.findAll('button[aria-label^="Open turn"]').map((button) => button.attributes('aria-label'))).toEqual([
      'Open turn 2',
      'Open turn 3',
      'Open turn 1',
    ])
    expect(wrapper.text()).not.toContain('Turn 4')
    expect(wrapper.text()).not.toContain('Turn 6')
  })

  it('moves stale ancestor final markers to the latest visible leaf', () => {
    const wrapper = mount(TurnTreeGraphView, {
      props: {
        conversations: [{
          id: 'conversation-stale-final',
          final_turn_id: 'turn-1',
          roots: [{ id: 'turn-1', seq_no: 1, children: [{ id: 'turn-2', seq_no: 2 }] }],
        }],
      },
    })

    expect(wrapper.get('button[aria-label="Open turn 1"]').text()).not.toContain('Final')
    expect(wrapper.get('button[aria-label="Open turn 2"]').text()).toContain('Final')
  })

  it('pans from background pointer drags without treating nodes as the canvas', async () => {
    const wrapper = mount(TurnTreeGraphView, { props: { conversations: [conversations[0]] } })
    const svg = wrapper.get('svg')
    const before = wrapper.get('svg g').attributes('transform')

    await svg.trigger('pointerdown', { button: 0, pointerId: 7, clientX: 10, clientY: 10 })
    await svg.trigger('pointermove', { pointerId: 7, clientX: 35, clientY: 45 })
    await svg.trigger('pointerup', { pointerId: 7, clientX: 35, clientY: 45 })

    expect(wrapper.get('svg g').attributes('transform')).not.toBe(before)
  })
})
