<script setup lang="ts">
import {
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogOverlay,
  AlertDialogPortal,
  AlertDialogRoot,
  AlertDialogTitle,
} from 'reka-ui'
import { cn } from '../../../lib/utils'

withDefaults(defineProps<{
  open: boolean
  title: string
  description: string
  contentClass?: string
}>(), {
  contentClass: 'max-w-md',
})

const emit = defineEmits<{
  close: []
}>()

function handleOpenChange(open: boolean) {
  if (!open) emit('close')
}
</script>

<template>
  <AlertDialogRoot :open="open" @update:open="handleOpenChange">
    <AlertDialogPortal>
      <AlertDialogOverlay class="ui-alert-overlay modal-overlay layer-modal fixed inset-0" />
      <AlertDialogContent
        :class="cn('ui-alert-content modal-card fixed left-1/2 top-1/2 z-[91] w-[calc(100vw-2rem)] -translate-x-1/2 -translate-y-1/2 overflow-hidden text-left', contentClass)"
      >
        <div class="modal-header">
          <div class="flex items-center gap-3">
            <slot name="icon" />
            <AlertDialogTitle class="text-base font-semibold text-[var(--color-text-main)]">
              {{ title }}
            </AlertDialogTitle>
          </div>
        </div>

        <AlertDialogDescription class="px-6 py-4 text-sm text-[var(--color-text-muted)]">
          {{ description }}
        </AlertDialogDescription>

        <div class="modal-footer">
          <AlertDialogCancel as-child>
            <slot name="cancel" />
          </AlertDialogCancel>
          <AlertDialogAction as-child>
            <slot name="action" />
          </AlertDialogAction>
        </div>
      </AlertDialogContent>
    </AlertDialogPortal>
  </AlertDialogRoot>
</template>

<style scoped>
.ui-alert-overlay[data-state='open'] {
  animation: alert-overlay-in var(--motion-duration-standard) var(--motion-ease-standard);
}

.ui-alert-overlay[data-state='closed'] {
  animation: alert-overlay-out var(--motion-duration-fast) var(--motion-ease-standard);
}

.ui-alert-content[data-state='open'] {
  animation: alert-content-in var(--motion-duration-standard) var(--motion-ease-spring);
}

.ui-alert-content[data-state='closed'] {
  animation: alert-content-out var(--motion-duration-fast) var(--motion-ease-standard);
}

@keyframes alert-overlay-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes alert-overlay-out {
  from { opacity: 1; }
  to { opacity: 0; }
}

@keyframes alert-content-in {
  from { opacity: 0; transform: translate(-50%, -48%) scale(0.985); }
  to { opacity: 1; transform: translate(-50%, -50%) scale(1); }
}

@keyframes alert-content-out {
  from { opacity: 1; transform: translate(-50%, -50%) scale(1); }
  to { opacity: 0; transform: translate(-50%, -49%) scale(0.99); }
}

@media (prefers-reduced-motion: reduce) {
  .ui-alert-overlay,
  .ui-alert-content {
    animation-duration: 1ms !important;
  }
}
</style>
