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
      class="modal-overlay"
      @click="closeModal"
    ></div>

    <!-- Modal container -->
    <div class="flex min-h-full items-center justify-center p-4 text-center sm:p-0">
      <div
        class="relative transform overflow-hidden rounded-lg bg-white text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-md"
        @click.stop
      >
        <!-- Modal Header -->
        <div class="modal-header">
          <div class="flex items-center gap-3">
            <ExclamationTriangleIcon class="h-5 w-5 shrink-0" style="color: var(--color-warning);" />
            <h3 class="text-base font-semibold" id="modal-title" style="color: var(--color-text-main);">{{ title }}</h3>
          </div>
        </div>

        <!-- Modal Body -->
        <div class="px-6 py-4">
          <p class="text-sm" style="color: var(--color-text-muted);">{{ message }}</p>
        </div>

        <!-- Modal Footer -->
        <div class="modal-footer">
          <button @click="closeModal" class="btn-secondary text-sm px-4 py-2">{{ cancelText }}</button>
          <button @click="confirmAction" class="btn-danger text-sm px-4 py-2">{{ confirmText }}</button>
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