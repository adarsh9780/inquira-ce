<script setup lang="ts">
import { ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
import { AlertDialogShell } from '../ui/alert-dialog'
import { Button } from '../ui/button'

withDefaults(defineProps<{
  isOpen?: boolean
  title?: string
  message?: string
  confirmText?: string
  cancelText?: string
}>(), {
  isOpen: false,
  title: 'Confirm Action',
  message: 'Are you sure you want to proceed?',
  confirmText: 'Confirm',
  cancelText: 'Cancel',
})

const emit = defineEmits<{
  close: []
  confirm: []
}>()

</script>

<template>
  <AlertDialogShell
    :open="isOpen"
    :title="title"
    :description="message"
    @close="emit('close')"
  >
    <template #icon>
      <ExclamationTriangleIcon class="h-5 w-5 shrink-0 text-[var(--color-warning)]" aria-hidden="true" />
    </template>
    <template #cancel>
      <Button variant="secondary">{{ cancelText }}</Button>
    </template>
    <template #action>
      <Button variant="danger" @click="emit('confirm')">{{ confirmText }}</Button>
    </template>
  </AlertDialogShell>
</template>
