<template>
  <!-- Modal Overlay -->
  <div
    v-if="isOpen"
    class="fixed inset-0 z-[60] overflow-y-auto"
    aria-labelledby="modal-title"
    role="dialog"
    aria-modal="true"
  >
    <!-- Background overlay -->
    <div
      class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
      @click="closeModal"
    ></div>

    <!-- Modal container -->
    <div class="flex min-h-full items-center justify-center p-4 text-center sm:p-0">
      <div
        class="relative transform overflow-hidden rounded-lg bg-white text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-md"
        @click.stop
      >
        <!-- Modal Header -->
        <div class="bg-white px-6 py-4 border-b border-gray-200">
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <ExclamationTriangleIcon class="h-6 w-6 text-yellow-500" />
            </div>
            <div class="ml-3">
              <h3 class="text-lg font-semibold text-gray-900" id="modal-title">
                {{ title }}
              </h3>
            </div>
          </div>
        </div>

        <!-- Modal Body -->
        <div class="bg-white px-6 py-4">
          <div class="sm:flex sm:items-start">
            <div class="mt-3 text-center sm:mt-0 sm:text-left">
              <div class="mt-2">
                <p class="text-sm text-gray-500">
                  {{ message }}
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- Modal Footer -->
        <div class="bg-gray-50 px-6 py-4 flex justify-end space-x-3">
          <button
            @click="closeModal"
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
          >
            {{ cancelText }}
          </button>
          <button
            @click="confirmAction"
            class="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors"
          >
            {{ confirmText }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ExclamationTriangleIcon } from '@heroicons/vue/24/outline'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: 'Confirm Action'
  },
  message: {
    type: String,
    default: 'Are you sure you want to proceed?'
  },
  confirmText: {
    type: String,
    default: 'Confirm'
  },
  cancelText: {
    type: String,
    default: 'Cancel'
  }
})

const emit = defineEmits(['close', 'confirm'])

function closeModal() {
  emit('close')
}

function confirmAction() {
  emit('confirm')
}

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && props.isOpen) {
    closeModal()
  }
})
</script>

<style scoped>
/* Custom styling for the confirmation modal */
</style>