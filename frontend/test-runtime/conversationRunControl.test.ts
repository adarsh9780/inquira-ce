import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useConversationRunControl } from '../src/composables/useConversationRunControl'
import { useExecutionStore } from '../src/stores/executionStore'

describe('conversation run control', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('aborts and clears only the selected conversation', () => {
    const execution = useExecutionStore()
    const first = new AbortController()
    const second = new AbortController()
    execution.setConversationRun('first', { abortController: first })
    execution.setConversationRun('second', { abortController: second })
    const control = useConversationRunControl(execution)

    expect(control.stopConversation('first')).toBe(true)
    expect(first.signal.aborted).toBe(true)
    expect(second.signal.aborted).toBe(false)
    expect(control.wasStopped('first')).toBe(true)

    control.clearStopped('first')
    expect(control.wasStopped('first')).toBe(false)
  })
})
