import { describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'

import { useChatAttachments } from '../src/composables/useChatAttachments'

describe('useChatAttachments', () => {
  it('formats attachment sizes for the tray', () => {
    const attachments = useChatAttachments()

    expect(attachments.formatAttachmentSize(0)).toBe('Image')
    expect(attachments.formatAttachmentSize(512)).toBe('512 B')
    expect(attachments.formatAttachmentSize(2048)).toBe('2.0 KB')
  })

  it('blocks attachment selection when the active model has no image support', async () => {
    const notifyError = vi.fn()
    const attachments = useChatAttachments({
      supported: ref(false),
      notifyError,
    })

    await attachments.appendPendingAttachments([
      new File(['image'], 'chart.png', { type: 'image/png' }),
    ])

    expect(attachments.pendingAttachments.value).toEqual([])
    expect(notifyError).toHaveBeenCalledWith(
      'Images Not Supported',
      'Switch to a vision-capable model before attaching images.',
    )
  })

  it('clears drag state when the pointer leaves the composer', () => {
    const attachments = useChatAttachments({ supported: ref(true) })

    attachments.handleAttachmentDragEnter()
    expect(attachments.isAttachmentDragActive.value).toBe(true)

    attachments.handleAttachmentDragLeave()
    expect(attachments.isAttachmentDragActive.value).toBe(false)
  })
})
