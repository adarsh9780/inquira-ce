import { ref } from 'vue'
import { SUPPORTED_CHAT_IMAGE_TYPES } from '../utils/modelCapabilities'

export function useChatAttachments({
  supported,
  inputRef,
  notifyError = () => {},
} = {}) {
  const pendingAttachments = ref([])
  const isAttachmentDragActive = ref(false)
  const dragDepth = ref(0)

  function formatAttachmentSize(size) {
    const bytes = Number(size || 0)
    if (!Number.isFinite(bytes) || bytes <= 0) return 'Image'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  function imagesSupported() {
    return Boolean(supported?.value ?? supported)
  }

  function buildAttachmentId(file) {
    return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}-${String(file?.name || 'image')}`
  }

  function openAttachmentPicker() {
    if (!imagesSupported()) {
      notifyError('Images Not Supported', 'The selected model does not support image attachments.')
      return
    }
    inputRef?.value?.click()
  }

  function fileToBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => {
        const result = String(reader.result || '')
        resolve(result.includes(',') ? result.split(',')[1] : result)
      }
      reader.onerror = () => reject(reader.error || new Error('Failed to read image file.'))
      reader.readAsDataURL(file)
    })
  }

  async function appendPendingAttachments(files) {
    if (!imagesSupported()) {
      notifyError('Images Not Supported', 'Switch to a vision-capable model before attaching images.')
      return
    }
    const normalizedFiles = Array.from(files || []).filter(
      (file) => SUPPORTED_CHAT_IMAGE_TYPES.has(String(file?.type || '').toLowerCase()),
    )
    if (normalizedFiles.length === 0) {
      notifyError('Unsupported File', 'Only PNG, JPG, WEBP, and GIF images can be attached.')
      return
    }

    for (const file of normalizedFiles) {
      const dataBase64 = await fileToBase64(file)
      pendingAttachments.value.push({
        attachment_id: buildAttachmentId(file),
        filename: String(file.name || 'image'),
        media_type: String(file.type || 'image/png'),
        data_base64: dataBase64,
        preview_url: `data:${String(file.type || 'image/png')};base64,${dataBase64}`,
        size: Number(file.size || 0),
      })
    }
  }

  async function handleAttachmentSelection(event) {
    try {
      await appendPendingAttachments(event?.target?.files || [])
    } catch (error) {
      notifyError('Image Attach Failed', error instanceof Error ? error.message : 'Failed to attach image.')
    } finally {
      if (event?.target) event.target.value = ''
    }
  }

  function removePendingAttachment(attachmentId) {
    const targetId = String(attachmentId || '').trim()
    pendingAttachments.value = pendingAttachments.value.filter(
      (item) => String(item?.attachment_id || '') !== targetId,
    )
  }

  function handleAttachmentDragEnter() {
    dragDepth.value += 1
    if (imagesSupported()) isAttachmentDragActive.value = true
  }

  function handleAttachmentDragOver() {
    if (imagesSupported()) isAttachmentDragActive.value = true
  }

  function handleAttachmentDragLeave() {
    dragDepth.value = Math.max(0, dragDepth.value - 1)
    if (dragDepth.value === 0) isAttachmentDragActive.value = false
  }

  async function handleAttachmentDrop(event) {
    dragDepth.value = 0
    isAttachmentDragActive.value = false
    try {
      await appendPendingAttachments(event?.dataTransfer?.files || [])
    } catch (error) {
      notifyError('Image Attach Failed', error instanceof Error ? error.message : 'Failed to attach image.')
    }
  }

  return {
    pendingAttachments,
    isAttachmentDragActive,
    formatAttachmentSize,
    openAttachmentPicker,
    appendPendingAttachments,
    handleAttachmentSelection,
    removePendingAttachment,
    handleAttachmentDragEnter,
    handleAttachmentDragOver,
    handleAttachmentDragLeave,
    handleAttachmentDrop,
  }
}
