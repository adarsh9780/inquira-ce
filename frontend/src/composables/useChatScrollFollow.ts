export function useChatScrollFollow() {
  function shouldFollowScroll(distanceFromBottom: unknown, threshold = 120): boolean {
    return Number(distanceFromBottom || 0) <= threshold
  }

  return {
    shouldFollowScroll,
  }
}
