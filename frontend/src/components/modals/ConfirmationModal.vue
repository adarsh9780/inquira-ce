<template>
  <AlertDialog :open="isOpen" @update:open="handleOpenChange">
    <AlertDialogContent
      class="max-w-md gap-0 overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-panel-elevated)] p-0 shadow-[var(--shadow-modal)] sm:max-w-md"
      data-testid="confirmation-dialog"
    >
      <AlertDialogHeader class="modal-header space-y-0 text-left">
        <div class="flex items-center gap-3">
          <ExclamationTriangleIcon
            class="h-5 w-5 shrink-0 text-[var(--color-warning)]"
            aria-hidden="true"
          />
          <AlertDialogTitle class="text-base font-semibold text-[var(--color-text-main)]">
            {{ title }}
          </AlertDialogTitle>
        </div>
      </AlertDialogHeader>

      <AlertDialogDescription class="px-6 py-4 text-sm text-[var(--color-text-muted)]">
        {{ message }}
      </AlertDialogDescription>

      <AlertDialogFooter class="modal-footer m-0 rounded-none border-t border-[var(--color-border)] bg-[var(--color-surface)] p-3">
        <AlertDialogCancel
          class="btn-secondary h-8 px-4 text-sm"
        >
          {{ cancelText }}
        </AlertDialogCancel>
        <AlertDialogAction
          variant="destructive"
          class="btn-danger h-8 px-4 text-sm"
          @click="confirmAction"
        >
          {{ confirmText }}
        </AlertDialogAction>
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
</template>

<script setup lang="ts">
import { ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'

interface Props {
  isOpen?: boolean
  title?: string
  message?: string
  confirmText?: string
  cancelText?: string
}

withDefaults(defineProps<Props>(), {
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

function closeModal() {
  emit('close')
}

function confirmAction() {
  emit('confirm')
}

function handleOpenChange(open: boolean) {
  if (!open) closeModal()
}
</script>
