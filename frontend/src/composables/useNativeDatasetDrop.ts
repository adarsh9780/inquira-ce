import { onMounted, onUnmounted } from 'vue'

export function useNativeDatasetDrop(openDatasetPicker: () => void) {
  function handleDatasetDragOver(event: DragEvent) {
    if (event.defaultPrevented || !event.dataTransfer?.types?.includes('Files')) return
    event.preventDefault()
  }

  function handleDatasetDrop(event: DragEvent) {
    if (event.defaultPrevented || !event.dataTransfer?.files?.length) return
    event.preventDefault()
    openDatasetPicker()
  }

  onMounted(() => {
    document.addEventListener('dragover', handleDatasetDragOver)
    document.addEventListener('drop', handleDatasetDrop)
    window.addEventListener('inquira:open-dataset-picker', openDatasetPicker)
  })
  onUnmounted(() => {
    document.removeEventListener('dragover', handleDatasetDragOver)
    document.removeEventListener('drop', handleDatasetDrop)
    window.removeEventListener('inquira:open-dataset-picker', openDatasetPicker)
  })

  return { handleDatasetDragOver, handleDatasetDrop }
}
