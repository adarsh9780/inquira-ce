<template>
  <!-- Progress Modal Overlay -->
  <div
    v-if="isVisible"
    class="fixed inset-0 z-50 overflow-y-auto"
    aria-labelledby="progress-modal-title"
    role="dialog"
    aria-modal="true"
  >
    <!-- Background overlay -->
    <div
      class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
      @click="handleCancel"
    ></div>

    <!-- Modal container -->
    <div class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
      <div
        class="relative transform overflow-hidden rounded-lg bg-white text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg max-h-[90vh] flex flex-col"
        @click.stop
      >
        <!-- Modal Header -->
        <div class="bg-white px-6 py-4 border-b border-gray-200">
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold text-gray-900" id="progress-modal-title">
              Saving Settings
            </h3>
            <button
              @click="handleCancel"
              :disabled="isCancelling"
              class="text-gray-400 hover:text-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <XMarkIcon class="h-6 w-6" />
            </button>
          </div>
        </div>

        <!-- Modal Body -->
        <div class="bg-white px-6 py-6 overflow-y-auto flex-1">
          <!-- Spinner and Timer -->
          <div class="flex flex-col items-center mb-6">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
            <div class="text-center">
              <p class="text-sm text-gray-600 mb-1">Processing your data...</p>
              <p class="text-xs text-gray-500">{{ formatElapsedTime(elapsedTime) }}</p>
            </div>
          </div>

          <!-- Current Progress Message -->
          <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div class="flex items-center space-x-3">
              <div class="animate-spin rounded-full h-5 w-5 border-2 border-blue-500 border-t-transparent"></div>
              <div class="flex-1">
                <p class="text-sm font-medium text-blue-900">
                  {{ currentMessage }}
                </p>
              </div>
            </div>
          </div>

          <!-- Interesting Fact Display -->
          <div v-if="currentFact" class="bg-gradient-to-r from-purple-50 to-pink-50 border border-purple-200 rounded-lg p-4 mt-4">
            <div class="flex items-start space-x-3">
              <div class="flex-shrink-0">
                <div class="w-6 h-6 bg-gradient-to-r from-purple-400 to-pink-400 rounded-full flex items-center justify-center">
                  <span class="text-white text-xs font-bold">💡</span>
                </div>
              </div>
              <div class="flex-1">
                <div class="flex items-center space-x-2 mb-1">
                  <span class="text-xs font-semibold text-purple-700 uppercase tracking-wide">Did You Know?</span>
                  <div class="h-px bg-gradient-to-r from-purple-300 to-pink-300 flex-1"></div>
                </div>
                <p class="text-sm text-gray-800 leading-relaxed">
                  {{ currentFact }}
                </p>
              </div>
            </div>
          </div>

          <!-- Connection Status -->
          <div class="mt-6 pt-4 border-t border-gray-200">
            <div class="flex items-center">
              <div
                class="w-2 h-2 rounded-full mr-2"
                :class="isConnected ? 'bg-green-500' : 'bg-red-500'"
              ></div>
              <span class="text-xs text-gray-500">
                {{ isConnected ? 'Connected' : 'Disconnected' }}
              </span>
            </div>
          </div>
        </div>

        <!-- Modal Footer -->
        <div class="bg-gray-50 px-6 py-4 flex justify-end">
          <button
            @click="handleCancel"
            :disabled="isCancelling"
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <div v-if="isCancelling" class="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-700 mr-2"></div>
            {{ isCancelling ? 'Cancelling...' : 'Cancel' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onUnmounted } from 'vue'
import {
  XMarkIcon,
  CheckCircleIcon,
  XCircleIcon
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