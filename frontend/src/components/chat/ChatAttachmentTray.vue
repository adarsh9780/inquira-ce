<template>
  <div v-if="attachments.length" class="px-4 pb-2">
    <div class="flex flex-wrap gap-2">
      <div
        v-for="attachment in attachments"
        :key="attachment.attachment_id"
        class="group/attachment flex items-center gap-2 rounded-xl border px-2 py-2"
        style="border-color: var(--color-border); background-color: color-mix(in srgb, var(--color-surface) 75%, transparent);"
      >
        <img
          :src="attachment.preview_url"
          :alt="attachment.filename"
          class="h-12 w-12 rounded-lg object-cover"
        />
        <div class="min-w-0">
          <p class="max-w-[150px] truncate text-xs font-medium" style="color: var(--color-text-main);">{{ attachment.filename }}</p>
          <p class="text-[11px]" style="color: var(--color-text-muted);">{{ formatSize(attachment.size) }}</p>
        </div>
        <button
          type="button"
          class="btn-icon opacity-70 transition-opacity group-hover/attachment:opacity-100"
          title="Remove image"
          @click="emit('remove', attachment.attachment_id)"
        >
          <XMarkIcon class="h-4 w-4" />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { XMarkIcon } from '@heroicons/vue/24/outline'

defineProps({
  attachments: {
    type: Array,
    default: () => [],
  },
  formatSize: {
    type: Function,
    required: true,
  },
})

const emit = defineEmits(['remove'])
</script>
