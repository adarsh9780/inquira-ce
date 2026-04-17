<template>
  <div
    v-if="isVisible"
    class="max-w-sm w-full animate-toast-in"
  >
    <div
      class="flex items-start gap-3 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-4"
      style="box-shadow: var(--shadow-lifted);"
    >
      <!-- Icon -->
      <div class="flex-shrink-0 mt-0.5">
        <CheckCircleIcon v-if="type === 'success'" class="h-5 w-5 text-[var(--color-success)]" />
        <ExclamationTriangleIcon v-else-if="type === 'error'" class="h-5 w-5 text-[var(--color-error)]" />
        <ExclamationCircleIcon v-else-if="type === 'warning'" class="h-5 w-5 text-[var(--color-warning)]" />
        <InformationCircleIcon v-else class="h-5 w-5 text-[var(--color-accent)]" />
      </div>

      <!-- Message -->
      <div class="flex-1 min-w-0">
        <p class="text-sm font-medium text-[var(--color-text-main)]">{{ title }}</p>
        <p v-if="message" class="text-sm text-[var(--color-text-muted)] mt-0.5">{{ message }}</p>
      </div>

      <!-- Close button -->
      <button
        @click="close"
        class="flex-shrink-0 text-[var(--color-text-muted)] hover:text-[var(--color-text-main)] transition-colors p-0.5 -mr-1"
      >
        <XMarkIcon class="h-4 w-4" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ExclamationCircleIcon,
  InformationCircleIcon,
  XMarkIcon
} from '@heroicons/vue/24/outline'

const props = defineProps({
  isVisible: {
    type: Boolean,
    default: false
  },
  type: {
    type: String,
    default: 'info',
    validator: (value) => ['success', 'error', 'warning', 'info'].includes(value)
  },
  title: {
    type: String,
    required: true
  },
  message: {
    type: String,
    default: ''
  },
  duration: {
    type: Number,
    default: 5000 // 5 seconds
  }
})

const emit = defineEmits(['close'])

let timeoutId = null

function close() {
  emit('close')
}

function startTimer() {
  if (timeoutId) {
    clearTimeout(timeoutId)
  }
  if (props.duration > 0) {
    timeoutId = setTimeout(() => {
      close()
    }, props.duration)
  }
}

function clearTimer() {
  if (timeoutId) {
    clearTimeout(timeoutId)
    timeoutId = null
  }
}

// Start timer when component becomes visible
watch(() => props.isVisible, (isVisible) => {
  if (isVisible) {
    startTimer()
  } else {
    clearTimer()
  }
})

// Cleanup on unmount
import { onUnmounted } from 'vue'
onUnmounted(() => {
  clearTimer()
})
</script>

<style scoped>
@keyframes toast-in {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-toast-in {
  animation: toast-in 0.2s ease-out forwards;
}
</style>
