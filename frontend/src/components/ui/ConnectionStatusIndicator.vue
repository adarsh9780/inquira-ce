<template>
  <!-- Only show when disconnected -->
  <div
    v-if="!isConnected && showIndicator"
    class="fixed top-4 right-4 z-50 bg-red-50 border border-red-200 rounded-lg p-4 shadow-lg max-w-sm"
  >
    <div class="flex items-center space-x-3">
      <!-- Animated warning icon -->
      <div class="flex-shrink-0">
        <div class="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
          <svg
            class="w-5 h-5 text-red-600 animate-pulse"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"
            />
          </svg>
        </div>
      </div>

      <!-- Status text -->
      <div class="flex-1 min-w-0">
        <p class="text-sm font-medium text-red-800">
          Backend Connection Lost
        </p>
        <p class="text-xs text-red-600 mt-1">
          Attempting to reconnect...
        </p>
        <p class="text-xs text-red-500 mt-1 font-mono">
          {{ formattedTimeSinceDisconnect }}
        </p>
      </div>

      <!-- Retry indicator -->
      <div class="flex-shrink-0">
        <div class="flex items-center space-x-1">
          <div
            v-for="n in 3"
            :key="n"
            class="w-2 h-2 bg-red-400 rounded-full animate-pulse"
            :style="{ animationDelay: `${n * 0.2}s` }"
          />
        </div>
      </div>
    </div>

    <!-- Progress bar for retry attempts -->
    <div class="mt-3">
      <div class="w-full bg-red-200 rounded-full h-1.5">
        <div
          class="bg-red-600 h-1.5 rounded-full transition-all duration-1000 ease-out"
          :style="{ width: `${retryProgress}%` }"
        />
      </div>
      <p class="text-xs text-red-600 mt-1 text-center">
        Next retry in {{ secondsUntilRetry }}s
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { settingsWebSocket } from '../../services/websocketService'

const isConnected = ref(true)
const showIndicator = ref(false)
const disconnectTime = ref(null)
const retryInterval = ref(null)
const secondsUntilRetry = ref(5)
const retryProgress = ref(0)

// Format time since disconnect
const formattedTimeSinceDisconnect = computed(() => {
  if (!disconnectTime.value) return '0s'

  const now = Date.now()
  const elapsed = Math.floor((now - disconnectTime.value) / 1000)

  if (elapsed < 60) {
    return `${elapsed}s`
  } else if (elapsed < 3600) {
    const minutes = Math.floor(elapsed / 60)
    const seconds = elapsed % 60
    return `${minutes}m ${seconds}s`
  } else {
    const hours = Math.floor(elapsed / 3600)
    const minutes = Math.floor((elapsed % 3600) / 60)
    return `${hours}h ${minutes}m`
  }
})

// Setup WebSocket connection monitoring
function setupWebSocketMonitoring() {
  // Monitor connection status
  const unsubscribe = settingsWebSocket.onConnection((connected) => {
    const status = settingsWebSocket.getConnectionStatus()
    const shouldMonitor = Boolean(status.isPersistentMode || status.lastConnectionAttempt)
    if (!shouldMonitor) {
      isConnected.value = true
      showIndicator.value = false
      disconnectTime.value = null
      stopRetryTimer()
      return
    }

    isConnected.value = connected

    if (connected) {
      // Connection restored
      showIndicator.value = false
      disconnectTime.value = null
      stopRetryTimer()
    } else {
      // Connection lost
      disconnectTime.value = Date.now()
      showIndicator.value = true
      startRetryTimer()
    }
  })

  // Cleanup subscription on unmount
  onUnmounted(() => {
    if (typeof unsubscribe === 'function') unsubscribe()
  })

  // Start monitoring with current status
  const current = settingsWebSocket.getConnectionStatus()
  const shouldMonitor = Boolean(current.isPersistentMode || current.lastConnectionAttempt)
  isConnected.value = shouldMonitor ? settingsWebSocket.isConnected : true
  if (shouldMonitor && !isConnected.value) {
    disconnectTime.value = Date.now()
    showIndicator.value = true
    startRetryTimer()
  } else {
    showIndicator.value = false
  }
}

// Retry timer functionality
function startRetryTimer() {
  stopRetryTimer() // Clear any existing timer

  let countdown = 5
  secondsUntilRetry.value = countdown
  retryProgress.value = 0

  retryInterval.value = setInterval(() => {
    countdown--
    secondsUntilRetry.value = countdown
    retryProgress.value = ((5 - countdown) / 5) * 100

    if (countdown <= 0) {
      // Timer reached zero, will retry automatically via WebSocket service
      countdown = 5
      secondsUntilRetry.value = countdown
      retryProgress.value = 0
    }
  }, 1000)
}

function stopRetryTimer() {
  if (retryInterval.value) {
    clearInterval(retryInterval.value)
    retryInterval.value = null
  }
}

// Cleanup on unmount
onUnmounted(() => {
  stopRetryTimer()
})

// Initialize monitoring
onMounted(() => {
  setupWebSocketMonitoring()
})
</script>

<style scoped>
/* Custom animations for retry dots */
@keyframes pulse-delayed {
  0%, 80%, 100% {
    opacity: 0.3;
    transform: scale(0.8);
  }
  40% {
    opacity: 1;
    transform: scale(1);
  }
}

.animate-pulse {
  animation: pulse-delayed 1.5s infinite;
}
</style>
