import { computed, ref } from 'vue'

const toasts = ref([])
const notificationHistory = ref([])
const MAX_NOTIFICATION_HISTORY = 100
let toastId = 0

function normalizeDuration(duration, fallback) {
  const value = Number(duration)
  if (!Number.isFinite(value)) return fallback
  return Math.max(0, value)
}

function normalizeToastOptions(durationOrOptions, options = {}, fallbackDuration = 5000) {
  if (durationOrOptions && typeof durationOrOptions === 'object' && !Array.isArray(durationOrOptions)) {
    return {
      duration: normalizeDuration(durationOrOptions.duration, fallbackDuration),
      options: { ...durationOrOptions },
    }
  }
  return {
    duration: normalizeDuration(durationOrOptions, fallbackDuration),
    options: options && typeof options === 'object' ? { ...options } : {},
  }
}

function trimNotificationHistory() {
  if (notificationHistory.value.length <= MAX_NOTIFICATION_HISTORY) return
  notificationHistory.value.splice(MAX_NOTIFICATION_HISTORY)
}

export function useToast() {
  function showToast(type, title, message = '', durationOrOptions = 5000, options = {}) {
    const { duration, options: normalizedOptions } = normalizeToastOptions(
      durationOrOptions,
      options,
      5000,
    )
    const id = ++toastId
    const createdAt = Date.now()
    const normalizedTitle = String(title || '').trim() || 'Notification'
    const normalizedMessage = String(message || '').trim()
    const metadata = normalizedOptions?.metadata && typeof normalizedOptions.metadata === 'object'
      ? { ...normalizedOptions.metadata }
      : {}

    const toast = {
      id,
      type,
      title: normalizedTitle,
      message: normalizedMessage,
      duration,
      createdAt,
      source: String(normalizedOptions?.source || '').trim(),
      statusCode: Number.isFinite(Number(normalizedOptions?.statusCode))
        ? Number(normalizedOptions.statusCode)
        : null,
      category: String(normalizedOptions?.category || '').trim(),
      metadata,
      isVisible: true,
    }

    toasts.value.push(toast)
    notificationHistory.value.unshift({
      ...toast,
      read: false,
    })
    trimNotificationHistory()

    return id
  }

  function removeToast(id) {
    const index = toasts.value.findIndex((toast) => toast.id === id)
    if (index > -1) {
      toasts.value.splice(index, 1)
    }
  }

  function clearAllToasts() {
    toasts.value = []
  }

  function markAllNotificationsRead() {
    notificationHistory.value = notificationHistory.value.map((entry) => ({
      ...entry,
      read: true,
    }))
  }

  function clearNotificationHistory() {
    notificationHistory.value = []
  }

  const unreadNotificationCount = computed(() => (
    notificationHistory.value.reduce((count, entry) => count + (entry?.read ? 0 : 1), 0)
  ))

  return {
    toasts,
    notificationHistory,
    unreadNotificationCount,
    showToast,
    removeToast,
    clearAllToasts,
    markAllNotificationsRead,
    clearNotificationHistory,
  }
}

export const toast = {
  success: (title, message = '', durationOrOptions = 5000, options = {}) => {
    const { showToast } = useToast()
    return showToast('success', title, message, durationOrOptions, options)
  },
  error: (title, message = '', durationOrOptions = 7000, options = {}) => {
    const { showToast } = useToast()
    return showToast('error', title, message, durationOrOptions, options)
  },
  warning: (title, message = '', durationOrOptions = 6000, options = {}) => {
    const { showToast } = useToast()
    return showToast('warning', title, message, durationOrOptions, options)
  },
  info: (title, message = '', durationOrOptions = 5000, options = {}) => {
    const { showToast } = useToast()
    return showToast('info', title, message, durationOrOptions, options)
  },
}
