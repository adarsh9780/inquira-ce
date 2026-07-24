import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

const SCROLL_THRESHOLD_PX = 100
const SHOW_SCROLL_BUTTON_THRESHOLD_PX = 220

export function useChatScrollFollow({
  chatContainer,
  end,
  history,
  lastMessageId,
  activeConversationId,
  isLoading,
  onContainerClick,
}) {
  const scrollHost = ref(null)
  const showScrollToBottomButton = ref(false)
  let shouldAutoScroll = true
  let mutationObserver = null
  let lastScrollTop = 0

  function resolveScrollHost() {
    const localContainer = chatContainer.value
    if (!localContainer) return null
    const host = localContainer.parentElement?.closest?.('[data-chat-scroll-container]')
    return host || localContainer
  }

  function getScrollContainer() {
    return scrollHost.value || chatContainer.value
  }

  function updateScrollState(options = {}) {
    const fromUserScroll = options?.fromUserScroll === true
    const previousTop = Number.isFinite(options?.previousTop) ? options.previousTop : lastScrollTop
    const container = getScrollContainer()
    if (!container) {
      shouldAutoScroll = true
      showScrollToBottomButton.value = false
      lastScrollTop = 0
      return
    }
    const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight
    const isNearBottomNow = distanceFromBottom <= SCROLL_THRESHOLD_PX
    if (fromUserScroll) {
      if (container.scrollTop < previousTop && distanceFromBottom > 0) {
        shouldAutoScroll = false
      } else if (isNearBottomNow) {
        shouldAutoScroll = true
      }
    } else {
      shouldAutoScroll = isNearBottomNow
    }
    showScrollToBottomButton.value = distanceFromBottom > SHOW_SCROLL_BUTTON_THRESHOLD_PX
    lastScrollTop = container.scrollTop
  }

  function scrollToBottom(options = {}) {
    const resolvedBehavior = String(options?.behavior || '').trim() || (isLoading.value ? 'auto' : 'smooth')
    const force = options?.force === true
    const hardAlign = options?.hardAlign === true
    nextTick(() => {
      const container = getScrollContainer()
      const endEl = end.value
      if (!container) return
      if (force) {
        shouldAutoScroll = true
        showScrollToBottomButton.value = false
      }
      if (typeof container.scrollTo === 'function') {
        container.scrollTo({ top: container.scrollHeight, behavior: resolvedBehavior })
        if (hardAlign && force && resolvedBehavior === 'auto') {
          window.requestAnimationFrame(() => {
            container.scrollTo({ top: container.scrollHeight, behavior: 'auto' })
            updateScrollState()
          })
          return
        }
        window.requestAnimationFrame(updateScrollState)
        return
      }
      if (!endEl) return
      endEl.scrollIntoView({ behavior: resolvedBehavior, block: 'end' })
      window.requestAnimationFrame(updateScrollState)
    })
  }

  function handleScroll() {
    updateScrollState({ fromUserScroll: true, previousTop: lastScrollTop })
  }

  function handleScrollToBottomClick() {
    scrollToBottom({ behavior: 'auto', force: true })
  }

  onMounted(() => {
    scrollHost.value = resolveScrollHost()
    shouldAutoScroll = true
    showScrollToBottomButton.value = false
    const container = getScrollContainer()
    if (container) {
      lastScrollTop = container.scrollTop
      container.addEventListener('scroll', handleScroll, { passive: true })
      if (onContainerClick) container.addEventListener('click', onContainerClick)
    }
    if (chatContainer.value) {
      mutationObserver = new MutationObserver(() => {
        if (shouldAutoScroll) scrollToBottom()
      })
      mutationObserver.observe(chatContainer.value, { childList: true, subtree: true })
    }
    if (history.value.length > 0) {
      nextTick(() => scrollToBottom())
      window.setTimeout(() => scrollToBottom({ behavior: 'auto', force: true, hardAlign: true }), 32)
    }
  })

  onUnmounted(() => {
    const container = getScrollContainer()
    if (container) {
      container.removeEventListener('scroll', handleScroll)
      if (onContainerClick) container.removeEventListener('click', onContainerClick)
    }
    mutationObserver?.disconnect()
  })

  watch([() => history.value.length, lastMessageId], ([newLength], [oldLength]) => {
    const previousLength = Number.isFinite(oldLength) ? oldLength : 0
    if (shouldAutoScroll && newLength > previousLength) nextTick(() => scrollToBottom())
  })

  watch(activeConversationId, () => {
    shouldAutoScroll = true
    nextTick(() => scrollToBottom())
  })

  watch(isLoading, () => {
    if (shouldAutoScroll) nextTick(() => scrollToBottom())
  })

  return {
    scrollHost,
    showScrollToBottomButton,
    scrollToBottom,
    handleScrollToBottomClick,
  }
}
