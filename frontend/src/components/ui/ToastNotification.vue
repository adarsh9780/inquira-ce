<template>
  <div
    v-if="isVisible"
    class="fixed top-4 right-4 z-50 max-w-sm w-full"
  >
    <div
      class="bg-white border rounded-lg shadow-lg p-4 flex items-start space-x-3"
      :class="{
        'border-green-200 bg-green-50': type === 'success',
        'border-red-200 bg-red-50': type === 'error',
        'border-yellow-200 bg-yellow-50': type === 'warning',
        'border-blue-200 bg-blue-50': type === 'info'
      }"
    >
      <!-- Icon -->
      <div class="flex-shrink-0">
        <CheckCircleIcon v-if="type === 'success'" class="h-5 w-5 text-green-600" />
        <ExclamationTriangleIcon v-else-if="type === 'error'" class="h-5 w-5 text-red-600" />
        <ExclamationCircleIcon v-else-if="type === 'warning'" class="h-5 w-5 text-yellow-600" />
        <InformationCircleIcon v-else class="h-5 w-5 text-blue-600" />
      </div>

      <!-- Message -->
      <div class="flex-1 min-w-0">
        <p class="text-sm font-medium text-gray-900">{{ title }}</p>
        <p v-if="message" class="text-sm text-gray-700 mt-1">{{ message }}</p>
      </div>

      <!-- Close button -->
      <button
        @click="close"
        class="flex-shrink-0 ml-2 text-gray-400 hover:text-gray-600 transition-colors"
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