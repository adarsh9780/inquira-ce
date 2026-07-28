<script setup lang="ts">
import {
  DialogContent,
  DialogDescription,
  DialogOverlay,
  DialogPortal,
  DialogRoot,
  DialogTitle,
  VisuallyHidden,
} from 'reka-ui'
import { cn } from '../../../lib/utils'

const props = withDefaults(defineProps<{
  open: boolean
  title: string
  description?: string
  contentClass?: string
  closeOnOutside?: boolean
  headerless?: boolean
}>(), {
  description: '',
  contentClass: 'max-w-lg',
  closeOnOutside: true,
  headerless: false,
})

const emit = defineEmits<{
  close: []
}>()

function handleOpenChange(open: boolean) {
  if (!open) emit('close')
}

function handleOutside(event: Event) {
  if (!props.closeOnOutside) event.preventDefault()
}
</script>

<template>
  <DialogRoot :open="open" @update:open="handleOpenChange">
    <DialogPortal>
      <DialogOverlay class="ui-dialog-overlay modal-overlay layer-modal" />
      <DialogContent
        :class="cn('ui-dialog-content modal-card fixed left-1/2 top-1/2 z-[91] flex max-h-[calc(100vh-2rem)] w-[calc(100vw-2rem)] -translate-x-1/2 -translate-y-1/2 flex-col overflow-hidden text-left', contentClass)"
        @pointer-down-outside="handleOutside"
      >
        <div v-if="!headerless" class="modal-header flex shrink-0 items-center justify-between gap-3">
          <div class="flex min-w-0 items-center gap-3">
            <slot name="icon" />
            <div class="min-w-0">
              <DialogTitle class="text-base font-semibold text-[var(--color-text-main)]">
                {{ title }}
              </DialogTitle>
              <DialogDescription
                v-if="description"
                class="mt-1 text-sm text-[var(--color-text-muted)]"
              >
                {{ description }}
              </DialogDescription>
            </div>
          </div>
          <slot name="header-actions" />
        </div>
        <VisuallyHidden v-else>
          <DialogTitle>{{ title }}</DialogTitle>
          <DialogDescription v-if="description">{{ description }}</DialogDescription>
        </VisuallyHidden>
        <slot />
        <slot name="footer" />
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>

<style scoped>
.ui-dialog-overlay {
  position: fixed;
  inset: 0;
}

.ui-dialog-overlay[data-state='open'] {
  animation: dialog-overlay-in var(--motion-duration-standard) var(--motion-ease-standard);
}

.ui-dialog-overlay[data-state='closed'] {
  animation: dialog-overlay-out var(--motion-duration-fast) var(--motion-ease-standard);
}

.ui-dialog-content[data-state='open'] {
  animation: dialog-content-in var(--motion-duration-standard) var(--motion-ease-spring);
}

.ui-dialog-content[data-state='closed'] {
  animation: dialog-content-out var(--motion-duration-fast) var(--motion-ease-standard);
}

@keyframes dialog-overlay-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes dialog-overlay-out {
  from { opacity: 1; }
  to { opacity: 0; }
}

@keyframes dialog-content-in {
  from { opacity: 0; translate: -50% calc(-50% + 0.5rem); }
  to { opacity: 1; translate: -50% -50%; }
}

@keyframes dialog-content-out {
  from { opacity: 1; translate: -50% -50%; }
  to { opacity: 0; translate: -50% calc(-50% + 0.25rem); }
}

@media (prefers-reduced-motion: reduce) {
  .ui-dialog-overlay,
  .ui-dialog-content {
    animation-duration: 1ms !important;
  }
}
</style>
