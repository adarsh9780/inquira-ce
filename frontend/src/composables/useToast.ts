import { computed, ref } from 'vue'

type RecordValue = Record<string, unknown>
export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface ToastOptions {
  duration?: unknown
  source?: unknown
  statusCode?: unknown
  category?: unknown
  metadata?: RecordValue
}

export interface ToastNotification {
  id: number
  type: ToastType
  title: string
  message: string
  duration: number
  createdAt: number
  source: string
  statusCode: number | null
  category: string
  metadata: RecordValue
  isVisible: boolean
}

export interface NotificationHistoryEntry extends ToastNotification {
  read: boolean
}

const toasts = ref<ToastNotification[]>([])
const notificationHistory = ref<NotificationHistoryEntry[]>([])
const MAX_NOTIFICATION_HISTORY = 100
const DUPLICATE_NOTIFICATION_WINDOW_MS = 60_000
let toastId = 0

function normalizeDuration(duration: unknown, fallback: number): number {
  const value = Number(duration)
  if (!Number.isFinite(value)) return fallback
  return Math.max(0, value)
}

function normalizeToastOptions(
  durationOrOptions: unknown,
  options: ToastOptions = {},
  fallbackDuration = 5000,
): { duration: number; options: ToastOptions } {
  if (durationOrOptions && typeof durationOrOptions === 'object' && !Array.isArray(durationOrOptions)) {
    const normalized = durationOrOptions as ToastOptions
    return {
      duration: normalizeDuration(normalized.duration, fallbackDuration),
      options: { ...normalized },
    }
  }
  return {
    duration: normalizeDuration(durationOrOptions, fallbackDuration),
    options: options && typeof options === 'object' ? { ...options } : {},
  }
}

function trimNotificationHistory(): void {
  if (notificationHistory.value.length <= MAX_NOTIFICATION_HISTORY) return
  notificationHistory.value.splice(MAX_NOTIFICATION_HISTORY)
}

function isDuplicateNotification(
  candidate: Pick<ToastNotification, 'type' | 'title' | 'message' | 'category'>,
  createdAt: number,
): boolean {
  return notificationHistory.value.some((entry) => (
    createdAt - Number(entry?.createdAt || 0) <= DUPLICATE_NOTIFICATION_WINDOW_MS
    && String(entry?.type || '') === candidate.type
    && String(entry?.title || '') === candidate.title
    && String(entry?.message || '') === candidate.message
    && String(entry?.category || '') === candidate.category
  ))
}

export function useToast() {
  function showToast(
    type: ToastType,
    title: unknown,
    message: unknown = '',
    durationOrOptions: unknown = 5000,
    options: ToastOptions = {},
  ): number {
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
    const category = String(normalizedOptions?.category || '').trim()

    const duplicateCandidate = {
      type,
      title: normalizedTitle,
      message: normalizedMessage,
      category,
    }
    if (isDuplicateNotification(duplicateCandidate, createdAt)) {
      return 0
    }

    const toast: ToastNotification = {
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
      category,
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

  function removeToast(id: number): void {
    const index = toasts.value.findIndex((toast) => toast.id === id)
    if (index > -1) {
      toasts.value.splice(index, 1)
    }
  }

  function clearAllToasts(): void {
    toasts.value = []
  }

  function markAllNotificationsRead(): void {
    notificationHistory.value = notificationHistory.value.map((entry) => ({
      ...entry,
      read: true,
    }))
  }

  function clearNotificationHistory(): void {
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
  success: (title: unknown, message: unknown = '', durationOrOptions: unknown = 5000, options: ToastOptions = {}) => {
    const { showToast } = useToast()
    return showToast('success', title, message, durationOrOptions, options)
  },
  error: (title: unknown, message: unknown = '', durationOrOptions: unknown = 7000, options: ToastOptions = {}) => {
    const { showToast } = useToast()
    return showToast('error', title, message, durationOrOptions, options)
  },
  warning: (title: unknown, message: unknown = '', durationOrOptions: unknown = 6000, options: ToastOptions = {}) => {
    const { showToast } = useToast()
    return showToast('warning', title, message, durationOrOptions, options)
  },
  info: (title: unknown, message: unknown = '', durationOrOptions: unknown = 5000, options: ToastOptions = {}) => {
    const { showToast } = useToast()
    return showToast('info', title, message, durationOrOptions, options)
  },
}
