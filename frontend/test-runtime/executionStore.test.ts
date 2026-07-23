import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useExecutionStore } from '../src/stores/executionStore'

describe('executionStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
  })

  it('isolates concurrent conversation runs and aborts only the target', () => {
    const store = useExecutionStore()
    const first = new AbortController()
    const second = new AbortController()

    store.setConversationRun('first', { abortController: first })
    store.setConversationRun('second', { abortController: second })
    expect(store.isConversationRunning('first')).toBe(true)
    expect(store.isConversationRunning('second')).toBe(true)

    expect(store.abortConversationRun('first')).toBe(true)
    expect(first.signal.aborted).toBe(true)
    expect(second.signal.aborted).toBe(false)
  })

  it('tracks code execution as a removable background operation', () => {
    const store = useExecutionStore()

    store.setCodeRunning(true)
    expect(store.isCodeRunning).toBe(true)
    expect(store.backgroundOperations).toHaveLength(1)

    store.setCodeRunning(false)
    expect(store.isCodeRunning).toBe(false)
    expect((store.backgroundOperations[0] as Record<string, unknown>).status).toBe('complete')

    vi.advanceTimersByTime(3500)
    expect(store.backgroundOperations).toHaveLength(0)
  })
})
