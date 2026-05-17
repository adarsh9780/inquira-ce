<template>
  <div
    v-if="isVisible"
    class="max-w-sm w-full animate-toast-in"
  >
    <div
      class="relative overflow-hidden flex items-start gap-3 rounded-lg border p-4"
      :class="containerClass"
      :style="{ boxShadow: 'var(--shadow-lifted)' }"
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
        <p class="text-sm font-medium" :class="titleClass">{{ title }}</p>
        <p v-if="message" class="mt-0.5 text-sm" :class="messageClass">{{ message }}</p>
      </div>

      <!-- Close button -->
      <button
        @click="close"
        class="flex-shrink-0 transition-colors p-0.5 -mr-1"
        :class="closeButtonClass"
      >
        <XMarkIcon class="h-4 w-4" />
      </button>

      <div
        v-if="duration > 0"
        class="pointer-events-none absolute inset-x-0 bottom-0 h-px origin-left"
        :class="progressBarClass"
        :style="{ animationDuration: `${duration}ms` }"
      ></div>
    </div>
  </div>
</template>

<script setup>
import { computed, watch } from 'vue'
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

const containerClass = computed(() => {
  if (props.type === 'success') {
    return 'border-[var(--color-success)]/35 bg-[var(--color-success-bg)]'
  }
  if (props.type === 'error') {
    return 'border-[var(--color-error)]/40 bg-[var(--color-danger-bg)]'
  }
  if (props.type === 'warning') {
    return 'border-[var(--color-warning)]/40 bg-[var(--color-warning-bg)]'
  }
  return 'border-[var(--color-info)]/35 bg-[var(--color-info-bg)]'
})

const titleClass = computed(() => {
  if (props.type === 'success') return 'text-[var(--color-success)]'
  if (props.type === 'error') return 'text-[var(--color-danger-text)]'
  if (props.type === 'warning') return 'text-[var(--color-warning-text)]'
  return 'text-[var(--color-info-text)]'
})

const messageClass = computed(() => {
  if (props.type === 'success') return 'text-[var(--color-success)]/90'
  if (props.type === 'error') return 'text-[var(--color-danger-text)]/90'
  if (props.type === 'warning') return 'text-[var(--color-warning-text)]/90'
  return 'text-[var(--color-info-text)]/90'
})

const closeButtonClass = computed(() => {
  if (props.type === 'success') return 'text-[var(--color-success)]/70 hover:text-[var(--color-success)]'
  if (props.type === 'error') return 'text-[var(--color-danger-text)]/70 hover:text-[var(--color-danger-text)]'
  if (props.type === 'warning') return 'text-[var(--color-warning-text)]/70 hover:text-[var(--color-warning-text)]'
  return 'text-[var(--color-info-text)]/70 hover:text-[var(--color-info-text)]'
})

const progressBarClass = computed(() => {
  if (props.type === 'success') return 'bg-[var(--color-success)] animate-toast-progress'
  if (props.type === 'error') return 'bg-[var(--color-error)] animate-toast-progress'
  if (props.type === 'warning') return 'bg-[var(--color-warning)] animate-toast-progress'
  return 'bg-[var(--color-info)] animate-toast-progress'
})

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
    transform: translateX(16px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.animate-toast-in {
  animation: toast-in 0.2s ease-out forwards;
}

@keyframes toast-progress {
  from {
    transform: scaleX(1);
  }
  to {
    transform: scaleX(0);
  }
}

.animate-toast-progress {
  animation-name: toast-progress;
  animation-timing-function: linear;
  animation-fill-mode: forwards;
}
</style>
