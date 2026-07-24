<template>
  <Dialog :open="isOpen" @update:open="handleOpenChange">
    <DialogContent
      :show-close-button="false"
      class="max-w-md gap-0 overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-panel-elevated)] p-0 shadow-[var(--shadow-modal)] sm:max-w-md"
      @open-auto-focus="handleOpenAutoFocus"
    >
      <DialogHeader class="modal-header space-y-1 text-left">
        <DialogTitle class="text-base font-semibold text-[var(--color-text-main)]">
          Rename Workspace
        </DialogTitle>
        <DialogDescription class="text-sm text-[var(--color-text-muted)]">
          Update the workspace name shown in workspace and chat selectors.
        </DialogDescription>
      </DialogHeader>

      <div class="space-y-3 px-5 py-4">
        <Label for="workspace-rename" class="text-sm font-medium text-[var(--color-text-main)]">
          Workspace Name
        </Label>
        <Input
          id="workspace-rename"
          ref="nameInputRef"
          v-model="name"
          maxlength="120"
          class="input-base"
          placeholder="e.g. IPL Analytics"
          @keydown.enter.prevent="submit"
        />
      </div>

      <DialogFooter class="modal-footer m-0 rounded-none border-t border-[var(--color-border)] bg-[var(--color-surface)] p-3">
        <DialogClose as-child>
          <Button variant="outline" :disabled="isSubmitting">
            Cancel
          </Button>
        </DialogClose>
        <Button :disabled="isSubmitting || !name.trim()" @click="submit">
          {{ isSubmitting ? 'Renaming…' : 'Rename Workspace' }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import type { ComponentPublicInstance } from 'vue'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

interface Props {
  isOpen?: boolean
  isSubmitting?: boolean
  initialName?: string
}

const props = withDefaults(defineProps<Props>(), {
  isOpen: false,
  isSubmitting: false,
  initialName: '',
})

const emit = defineEmits<{
  close: []
  submit: [name: string]
}>()

const name = ref('')
const nameInputRef = ref<ComponentPublicInstance | null>(null)

function submit() {
  const normalized = name.value.trim()
  if (!normalized) return
  emit('submit', normalized)
}

function handleOpenChange(open: boolean) {
  if (!open) emit('close')
}

async function focusAndSelectName() {
  await nextTick()
  const input = nameInputRef.value?.$el as HTMLInputElement | undefined
  input?.focus()
  input?.select()
}

function handleOpenAutoFocus(event: Event) {
  event.preventDefault()
  void focusAndSelectName()
}

watch(
  () => props.isOpen,
  (open) => {
    if (open) name.value = props.initialName.trim()
  },
  { immediate: true },
)
</script>
