<template>
  <div class="layer-toast fixed right-4 bottom-4 flex max-h-[calc(100vh-5rem)] flex-col items-end gap-2 overflow-hidden">
    <ToastNotification
      v-for="toast in toasts"
      :key="toast.id"
      :is-visible="toast.isVisible"
      :type="toast.type"
      :title="toast.title"
      :message="toast.message"
      :duration="toast.duration"
      @close="removeToast(toast.id)"
    />
  </div>
</template>

<script setup>
import { useToast } from '../../composables/useToast'
import ToastNotification from './ToastNotification.vue'

const { toasts, removeToast } = useToast()
</script>
