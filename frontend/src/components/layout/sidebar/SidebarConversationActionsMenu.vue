<template>
  <Teleport to="body">
    <div
      v-if="isOpen"
      class="fixed z-50 w-52 overflow-hidden rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-elevated)] py-1 shadow-lg"
      :style="menuStyle"
      data-conversation-actions-menu
      @keydown.esc.stop.prevent="emit('close')"
    >
      <div class="px-3 py-2 text-[12px] font-medium text-[var(--color-text-muted)]">
        {{ exactDate }}
      </div>
      <div class="my-1 h-px bg-[var(--color-border)] opacity-70" />
      <button
        type="button"
        class="w-full px-3 py-1.5 text-left text-[12px] font-medium text-[var(--color-text-main)] transition-colors hover:bg-[var(--color-panel-muted)]"
        @click.stop="emit('rename')"
      >
        Rename
      </button>
      <button
        type="button"
        class="w-full px-3 py-1.5 text-left text-[12px] font-medium text-[var(--color-danger)] transition-colors hover:bg-[var(--color-danger-bg)]"
        @click.stop="emit('delete')"
      >
        Delete
      </button>
    </div>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false,
  },
  position: {
    type: Object,
    default: () => ({ x: 0, y: 0 }),
  },
  exactDate: {
    type: String,
    default: 'No date available',
  },
})

const emit = defineEmits(['rename', 'delete', 'close'])

const menuStyle = computed(() => ({
  left: `${Number(props.position?.x || 0)}px`,
  top: `${Number(props.position?.y || 0)}px`,
}))
</script>
