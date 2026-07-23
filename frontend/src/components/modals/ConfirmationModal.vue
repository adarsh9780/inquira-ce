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
      ref="dialogRef"
      class="fixed inset-0 layer-modal overflow-y-auto"
      aria-labelledby="modal-title"
      role="dialog"
      aria-modal="true"
      @keydown="handleDialogKeydown"
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
            <button ref="cancelButtonRef" @click="closeModal" class="btn-secondary text-sm px-4 py-2">{{ cancelText }}</button>
            <button @click="confirmAction" class="btn-danger text-sm px-4 py-2">{{ confirmText }}</button>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
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
const dialogRef = ref(null)
const cancelButtonRef = ref(null)
let previouslyFocusedElement = null

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

function focusableElements() {
  return [...(dialogRef.value?.querySelectorAll(
    'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
  ) || [])]
}

function handleDialogKeydown(event) {
  if (event.key !== 'Tab') return
  const focusable = focusableElements()
  if (!focusable.length) return
  const first = focusable[0]
  const last = focusable[focusable.length - 1]
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}

watch(() => props.isOpen, async (isOpen) => {
  if (isOpen) {
    previouslyFocusedElement = document.activeElement instanceof HTMLElement ? document.activeElement : null
    await nextTick()
    cancelButtonRef.value?.focus?.()
    return
  }
  previouslyFocusedElement?.focus?.()
  previouslyFocusedElement = null
}, { immediate: true })

onMounted(() => {
  document.addEventListener('keydown', handleEscape)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleEscape)
  previouslyFocusedElement?.focus?.()
})
</script>

<style scoped>
/* Custom styling for the confirmation modal */
</style>
