export function useChatAttachments() {
  function formatAttachmentSize(size) {
    const bytes = Number(size || 0)
    if (!Number.isFinite(bytes) || bytes <= 0) return 'Image'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return {
    formatAttachmentSize,
  }
}
