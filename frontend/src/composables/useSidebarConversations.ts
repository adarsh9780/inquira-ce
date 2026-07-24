export const sidebarConversationPageSize = 5 as const

export function useSidebarConversations() {
  return {
    sidebarConversationPageSize,
  }
}
