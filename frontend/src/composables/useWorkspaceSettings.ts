import { nextTick, ref, watch, type Ref } from 'vue'

export const WORKSPACE_SETTINGS_SECTIONS = [
  { id: 'general', label: 'General' },
  { id: 'connections', label: 'Data sources' },
  { id: 'ai', label: 'AI' },
] as const

export function useWorkspaceSettings(initialSection: Ref<unknown>) {
  const activeWorkspaceSection = ref('general')

  function selectWorkspaceSection(section: unknown) {
    const normalized = String(section || '').trim().toLowerCase()
    const requested = normalized === 'data' ? 'connections' : normalized
    activeWorkspaceSection.value = WORKSPACE_SETTINGS_SECTIONS.some((item) => item.id === requested)
      ? requested
      : 'general'
  }

  function moveWorkspaceSection(direction: number, event?: KeyboardEvent) {
    const currentIndex = WORKSPACE_SETTINGS_SECTIONS.findIndex(
      (section) => section.id === activeWorkspaceSection.value,
    )
    const nextIndex = (
      currentIndex + direction + WORKSPACE_SETTINGS_SECTIONS.length
    ) % WORKSPACE_SETTINGS_SECTIONS.length
    activeWorkspaceSection.value = WORKSPACE_SETTINGS_SECTIONS[nextIndex].id
    void nextTick(() => {
      const target = event?.currentTarget as HTMLElement | null
      const tabs = target?.parentElement?.querySelectorAll<HTMLElement>('[role="tab"]') || []
      tabs[nextIndex]?.focus()
    })
  }

  watch(initialSection, selectWorkspaceSection, { immediate: true })

  return {
    workspaceSections: WORKSPACE_SETTINGS_SECTIONS,
    activeWorkspaceSection,
    selectWorkspaceSection,
    moveWorkspaceSection,
  }
}
