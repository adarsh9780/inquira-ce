import { ref } from 'vue'

const toasts = ref([])
let toastId = 0

export function useToast() {
  function showToast(type, title, message = '', duration = 5000) {
    const id = ++toastId
    const toast = {
      id,
      type,
      title,
      message,
      duration,
      isVisible: true
    }

    toasts.value.push(toast)

    // Auto remove after duration
    if (duration > 0) {
      setTimeout(() => {
        removeToast(id)
      }, duration)
    }

    return id
  }

  function removeToast(id) {
    const index = toasts.value.findIndex(toast => toast.id === id)
    if (index > -1) {
      toasts.value.splice(index, 1)
    }
  }

  function clearAllToasts() {
    toasts.value = []
  }

  return {
    toasts: toasts.value,
    showToast,
    removeToast,
    clearAllToasts
  }
}

// Global toast functions for convenience
export const toast = {
  success: (title, message = '', duration = 5000) => {
    const { showToast } = useToast()
    return showToast('success', title, message, duration)
  },
  error: (title, message = '', duration = 7000) => {
    const { showToast } = useToast()
    return showToast('error', title, message, duration)
  },
  warning: (title, message = '', duration = 6000) => {
    const { showToast } = useToast()
    return showToast('warning', title, message, duration)
  },
  info: (title, message = '', duration = 5000) => {
    const { showToast } = useToast()
    return showToast('info', title, message, duration)
  }
}