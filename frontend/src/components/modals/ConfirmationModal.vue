<template>
  <Transition
    enter-active-class="dialog-fade-enter-active dialog-pop-enter-active"
    enter-from-class="dialog-fade-enter-from dialog-pop-enter-from"
    leave-active-class="dialog-fade-leave-active dialog-pop-leave-active"
    leave-to-class="dialog-fade-leave-to dialog-pop-leave-to"
  >
    <!-- Modal Overlay -->
    <div
      v-if="isOpen"
      class="fixed inset-0 layer-modal overflow-y-auto"
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
          class="modal-card relative w-full max-w-md text-left sm:my-8"
          @click.stop
        >
          <!-- Modal Header -->
          <div class="modal-header">
            <div class="flex items-center gap-3">
              <ExclamationTriangleIcon class="h-5 w-5 shrink-0 text-[var(--color-warning)]" />
              <h3 class="text-base font-semibold text-[var(--color-text-main)]" id="modal-title">{{ title }}</h3>
            </div>
          </div>

          <!-- Modal Body -->
          <div class="px-6 py-4">
            <p class="text-sm text-[var(--color-text-muted)]">{{ message }}</p>
          </div>

          <!-- Modal Footer -->
          <div class="modal-footer">
            <button @click="closeModal" class="btn-secondary text-sm px-4 py-2">{{ cancelText }}</button>
            <button @click="confirmAction" class="btn-danger text-sm px-4 py-2">{{ confirmText }}</button>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
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

function handleEscape(e) {
  if (e.key === 'Escape' && props.isOpen) {
    closeModal()
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleEscape)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleEscape)
})
</script>

<style scoped>
/* Custom styling for the confirmation modal */
</style>
