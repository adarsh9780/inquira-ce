<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-[70] overflow-y-auto"
    role="dialog"
    aria-modal="true"
  >
    <div class="fixed inset-0 bg-gray-500 bg-opacity-70" @click="closeModal"></div>

    <div class="flex min-h-full items-center justify-center p-4">
      <div class="relative w-full max-w-md rounded-xl bg-white shadow-xl" @click.stop>
        <div class="border-b border-gray-200 px-5 py-4">
          <h3 class="text-base font-semibold text-gray-900">Create Workspace</h3>
          <p class="mt-1 text-sm text-gray-500">
            Organize datasets and chats in a dedicated workspace.
          </p>
        </div>

        <div class="px-5 py-4 space-y-3">
          <label for="workspace-name" class="text-sm font-medium text-gray-700">Workspace Name</label>
          <input
            id="workspace-name"
            ref="nameInputRef"
            v-model="name"
            type="text"
            maxlength="120"
            class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="e.g. IPL Analytics"
            @keydown.enter.prevent="submit"
          />
          <p class="text-xs text-gray-500">{{ planLabel }} plan</p>
        </div>

        <div class="flex justify-end gap-2 border-t border-gray-200 px-5 py-4">
          <button
            type="button"
            class="rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
            :disabled="isSubmitting"
            @click="closeModal"
          >
            Cancel
          </button>
          <button
            type="button"
            class="rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            :disabled="isSubmitting || !name.trim()"
            @click="submit"
          >
            {{ isSubmitting ? 'Creating...' : 'Create Workspace' }}
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
