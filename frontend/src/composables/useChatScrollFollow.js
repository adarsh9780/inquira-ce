export function useChatScrollFollow() {
  function shouldFollowScroll(distanceFromBottom, threshold = 120) {
    return Number(distanceFromBottom || 0) <= threshold
  }

  return {
    shouldFollowScroll,
  }
}
