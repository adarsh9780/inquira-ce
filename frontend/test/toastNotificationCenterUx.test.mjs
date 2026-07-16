import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { toast, useToast } from '../src/composables/useToast.js'

test('toast system keeps session history and renders right-edge timeout progress', () => {
  const toastComposable = readFileSync(resolve(process.cwd(), 'src/composables/useToast.js'), 'utf-8')
  const toastContainer = readFileSync(resolve(process.cwd(), 'src/components/ui/ToastContainer.vue'), 'utf-8')
  const toastNotification = readFileSync(resolve(process.cwd(), 'src/components/ui/ToastNotification.vue'), 'utf-8')

  assert.equal(toastComposable.includes('const notificationHistory = ref([])'), true)
  assert.equal(toastComposable.includes('const MAX_NOTIFICATION_HISTORY = 100'), true)
  assert.equal(toastComposable.includes('const DUPLICATE_NOTIFICATION_WINDOW_MS = 60_000'), true)
  assert.equal(toastComposable.includes('markAllNotificationsRead'), true)
  assert.equal(toastComposable.includes('clearNotificationHistory'), true)
  assert.equal(toastContainer.includes('class="layer-toast fixed right-4 bottom-4'), true)
  assert.equal(toastNotification.includes('const containerClass = computed(() => {'), true)
  assert.equal(toastNotification.includes("return 'border-[var(--color-error)]/40 bg-[var(--color-danger-bg)]'"), true)
  assert.equal(toastNotification.includes("return 'border-[var(--color-warning)]/40 bg-[var(--color-warning-bg)]'"), true)
  assert.equal(toastNotification.includes('class="pointer-events-none absolute inset-x-0 bottom-0 h-px origin-left"'), true)
  assert.equal(toastNotification.includes('animationDuration: `${duration}ms`'), true)
  assert.equal(toastNotification.includes('}, { immediate: true })'), true)
  assert.equal(toastNotification.includes('@keyframes toast-progress'), true)
})

test('toast system deduplicates repeated runtime errors while preserving distinct messages', () => {
  const { toasts, notificationHistory, clearAllToasts, clearNotificationHistory } = useToast()
  clearAllToasts()
  clearNotificationHistory()

  const firstId = toast.error('Workspace Runtime Error', 'Failed to start workspace runtime')
  const duplicateId = toast.error('Workspace Runtime Error', 'Failed to start workspace runtime')
  const distinctId = toast.error('Workspace Runtime Error', 'Workspace runtime bootstrap failed')

  assert.ok(firstId > 0)
  assert.equal(duplicateId, 0)
  assert.ok(distinctId > 0)
  assert.equal(toasts.value.length, 2)
  assert.equal(notificationHistory.value.length, 2)
})
