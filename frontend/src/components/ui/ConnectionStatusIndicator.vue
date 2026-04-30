<template>
  <!-- Only show when disconnected -->
  <div
    v-if="!isConnected && showIndicator"
    class="fixed top-4 right-4 z-50 max-w-sm rounded-lg border p-4 shadow-lg"
    style="background-color: var(--color-danger-bg); border-color: color-mix(in srgb, var(--color-danger) 35%, var(--color-border));"
  >
    <div class="flex items-center space-x-3">
      <!-- Animated warning icon -->
      <div class="flex-shrink-0">
        <div class="flex h-8 w-8 items-center justify-center rounded-full" style="background-color: color-mix(in srgb, var(--color-danger) 12%, var(--color-base));">
          <svg
            class="h-5 w-5 animate-pulse"
            style="color: var(--color-danger);"
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
        <p class="text-sm font-medium" style="color: var(--color-danger-text);">
          Backend Connection Lost
        </p>
        <p class="mt-1 text-xs" style="color: var(--color-danger-text);">
          Attempting to reconnect...
        </p>
        <p class="mt-1 text-xs font-mono" style="color: var(--color-danger-text);">
          {{ formattedTimeSinceDisconnect }}
        </p>
      </div>

      <!-- Retry indicator -->
      <div class="flex-shrink-0">
        <div class="flex items-center space-x-1">
          <div
            v-for="n in 3"
            :key="n"
            class="h-2 w-2 rounded-full animate-pulse"
            :style="{
              backgroundColor: 'color-mix(in srgb, var(--color-danger) 70%, var(--color-base))',
              animationDelay: `${n * 0.2}s`,
            }"
          />
        </div>
      </div>
    </div>

    <!-- Progress bar for retry attempts -->
    <div class="mt-3">
      <div class="h-1.5 w-full rounded-full" style="background-color: color-mix(in srgb, var(--color-danger) 18%, var(--color-base));">
        <div
          class="h-1.5 rounded-full transition-all duration-1000 ease-out"
          :style="{ width: `${retryProgress}%`, backgroundColor: 'var(--color-danger)' }"
        />
      </div>
      <p class="mt-1 text-center text-xs" style="color: var(--color-danger-text);">
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
