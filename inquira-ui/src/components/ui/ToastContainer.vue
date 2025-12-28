<template>
  <div class="fixed top-4 right-4 z-[100] space-y-2">
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
import { computed } from 'vue'
import { useToast } from '../../composables/useToast'
import ToastNotification from './ToastNotification.vue'

const { toasts, removeToast } = useToast()

// Make toasts reactive
const reactiveToasts = computed(() => toasts)
</script>