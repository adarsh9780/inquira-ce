import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

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
  it('renders separate accessible graphs and emits node selections', async () => {
    const wrapper = mount(TurnTreeGraphView, {
      props: { conversations, currentTurnId: 'turn-2', currentParentTurnId: 'turn-1', variant: 'page' },
    })

    expect(wrapper.findAll('[data-turn-tree-graph]')).toHaveLength(2)
    expect(wrapper.findAll('svg[role="img"]')).toHaveLength(2)
    expect(wrapper.text()).toContain('Final')
    expect(wrapper.findAll('button[aria-label^="Open turn"]')).toHaveLength(3)

    await wrapper.get('button[aria-label="Open turn 2"]').trigger('click')
    expect(wrapper.emitted('select')).toEqual([[{ conversationId: 'conversation-1', turnId: 'turn-2' }]])
  })

  it('opens shared actions from the visible node menu and emits actions', async () => {
    const wrapper = mount(TurnTreeGraphView, { props: { conversations } })

    await wrapper.get('button[aria-label="Actions for turn 1"]').trigger('click', { clientX: 20, clientY: 30 })
    expect(wrapper.text()).toContain('Mark Final')

    const markFinal = wrapper.findAll('[data-turn-tree-context-menu] button').find((button) => button.text() === 'Mark Final')
    await markFinal.trigger('click')
    expect(wrapper.emitted('mark-final')).toEqual([[{ conversationId: 'conversation-1', turnId: 'turn-1' }]])
  })

  it('opens shared actions when a node is right-clicked', async () => {
    const wrapper = mount(TurnTreeGraphView, { props: { conversations } })

    await wrapper.get('button[aria-label="Open turn 2"]').trigger('contextmenu', { clientX: 40, clientY: 50 })

    expect(wrapper.find('[data-turn-tree-context-menu]').exists()).toBe(true)
    expect(wrapper.find('[data-turn-tree-context-menu]').attributes('style')).toContain('left: 40px')
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
