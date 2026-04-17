<template>
  <Transition
    enter-active-class="dialog-fade-enter-active dialog-pop-enter-active"
    enter-from-class="dialog-fade-enter-from dialog-pop-enter-from"
    leave-active-class="dialog-fade-leave-active dialog-pop-leave-active"
    leave-to-class="dialog-fade-leave-to dialog-pop-leave-to"
  >
    <div
      v-if="isVisible"
      class="fixed inset-0 layer-modal overflow-y-auto"
      aria-labelledby="progress-modal-title"
      role="dialog"
      aria-modal="true"
    >
      <div class="modal-overlay" @click="handleCancel"></div>

      <div class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
        <div
          class="modal-card relative flex max-h-[90vh] w-full max-w-lg flex-col text-left sm:my-8"
          @click.stop
        >
        <div class="modal-header">
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold text-[var(--color-text-main)]" id="progress-modal-title">
              Saving Settings
            </h3>
            <button
              @click="handleCancel"
              :disabled="isCancelling"
              class="btn-icon disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <XMarkIcon class="h-6 w-6" />
            </button>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto px-6 py-6">
          <div class="flex flex-col items-center mb-6">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-[var(--color-accent)] mb-4"></div>
            <div class="text-center">
              <p class="mb-1 text-sm text-[var(--color-text-muted)]">Processing your data...</p>
              <p class="text-xs text-[var(--color-text-muted)]">{{ formatElapsedTime(elapsedTime) }}</p>
            </div>
          </div>

          <div class="bg-[var(--color-accent-soft)] border border-[var(--color-accent-border)] rounded-lg p-4">
            <div class="flex items-center space-x-3">
              <div class="animate-spin rounded-full h-5 w-5 border-2 border-[var(--color-accent)] border-t-transparent"></div>
              <div class="flex-1">
                <p class="text-sm font-medium text-[var(--color-accent)]">
                  {{ currentMessage }}
                </p>
              </div>
            </div>
          </div>

          <div v-if="currentFact" class="mt-4 rounded-lg border border-[var(--color-info)]/25 bg-[var(--color-info-bg)] p-4">
            <div class="flex items-start space-x-3">
              <div class="flex-shrink-0">
                <div class="flex h-6 w-6 items-center justify-center rounded-full bg-[var(--color-info)]">
                  <span class="text-white text-xs font-bold">💡</span>
                </div>
              </div>
              <div class="flex-1">
                <div class="flex items-center space-x-2 mb-1">
                  <span class="text-xs font-semibold uppercase tracking-wide text-[var(--color-info)]">Did You Know?</span>
                  <div class="h-px flex-1 bg-[var(--color-info)]/30"></div>
                </div>
                <p class="text-sm leading-relaxed text-[var(--color-text-main)]">
                  {{ currentFact }}
                </p>
              </div>
            </div>
          </div>

          <div class="mt-6 border-t border-[var(--color-border)] pt-4">
            <div class="flex items-center">
              <div
                class="mr-2 h-2 w-2 rounded-full"
                :class="isConnected ? 'status-dot-green' : 'status-dot-red'"
              ></div>
              <span class="text-xs text-[var(--color-text-muted)]">
                {{ isConnected ? 'Connected' : 'Disconnected' }}
              </span>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button
            @click="handleCancel"
            :disabled="isCancelling"
            class="btn-secondary px-4 py-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span v-if="isCancelling" class="mr-2 inline-block h-4 w-4 animate-spin rounded-full border-b-2 border-[var(--color-text-main)]"></span>
            {{ isCancelling ? 'Cancelling...' : 'Cancel' }}
          </button>
        </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { ref, watch, onUnmounted } from 'vue'
import {
  XMarkIcon
} from '@heroicons/vue/24/outline'

const props = defineProps({
  isVisible: {
    type: Boolean,
    default: false
  },
  currentMessage: {
    type: String,
    default: 'Processing your request...'
  },
  currentFact: {
    type: String,
    default: ''
  },
  isConnected: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['cancel', 'close'])

const isCancelling = ref(false)
const startTime = ref(null)
const elapsedTime = ref(0)
const timerInterval = ref(null)

// Timer functionality
const startTimer = () => {
  startTime.value = Date.now()
  elapsedTime.value = 0
  timerInterval.value = setInterval(() => {
    elapsedTime.value = Date.now() - startTime.value
  }, 100)
}

const stopTimer = () => {
  if (timerInterval.value) {
    clearInterval(timerInterval.value)
    timerInterval.value = null
  }
}

const formatElapsedTime = (ms) => {
  const seconds = Math.floor(ms / 1000)
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60

  if (minutes > 0) {
    return `${minutes}m ${remainingSeconds}s`
  }
  return `${remainingSeconds}s`
}

// Watch for modal visibility to start/stop timer
watch(() => props.isVisible, (newValue) => {
  if (newValue) {
    startTimer()
  } else {
    stopTimer()
  }
})

// Cleanup timer on component unmount
onUnmounted(() => {
  stopTimer()
})

function handleCancel() {
  if (isCancelling.value) return

  isCancelling.value = true
  stopTimer()
  emit('cancel')
}

// Reset cancelling state when modal becomes invisible
watch(() => props.isVisible, (newValue) => {
  if (!newValue) {
    isCancelling.value = false
  }
})
</script>
