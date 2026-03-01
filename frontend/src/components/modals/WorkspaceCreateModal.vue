<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-[70] overflow-y-auto"
    role="dialog"
    aria-modal="true"
  >
    <div class="modal-overlay" @click="closeModal"></div>

    <div class="flex min-h-full items-center justify-center p-4">
      <div class="relative w-full max-w-md modal-card" @click.stop>
        <div class="modal-header flex-col items-start">
          <h3 class="text-base font-semibold" style="color: var(--color-text-main);">Create Workspace</h3>
          <p class="mt-1 text-sm" style="color: var(--color-text-muted);">
            Organize datasets and chats in a dedicated workspace.
          </p>
        </div>

        <div class="px-5 py-4 space-y-3">
          <label for="workspace-name" class="text-sm font-medium" style="color: var(--color-text-main);">Workspace Name</label>
          <input
            id="workspace-name"
            ref="nameInputRef"
            v-model="name"
            type="text"
            maxlength="120"
            class="input-base"
            placeholder="e.g. IPL Analytics"
            @keydown.enter.prevent="submit"
          />
          <p class="text-xs" style="color: var(--color-text-muted);">{{ planLabel }} plan</p>
        </div>

        <div class="modal-footer">
          <button type="button" class="btn-secondary text-sm px-4 py-2" :disabled="isSubmitting" @click="closeModal">Cancel</button>
          <button type="button" class="btn-primary text-sm px-4 py-2" :disabled="isSubmitting || !name.trim()" @click="submit">
            {{ isSubmitting ? 'Creating…' : 'Create Workspace' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  isSubmitting: {
    type: Boolean,
    default: false
  },
  plan: {
    type: String,
    default: 'FREE'
  }
})

const emit = defineEmits(['close', 'submit'])

const name = ref('')
const nameInputRef = ref(null)

const planLabel = computed(() => `${String(props.plan || 'FREE').toUpperCase()}`)

function closeModal() {
  emit('close')
}

function submit() {
  if (!name.value.trim()) return
  emit('submit', name.value.trim())
}

watch(
  () => props.isOpen,
  async (open) => {
    if (open) {
      name.value = ''
      await nextTick()
      nameInputRef.value?.focus()
    }
  }
)

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && props.isOpen) {
    closeModal()
  }
})
</script>
