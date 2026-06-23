<template>
  <FloatingActionMenu
    :is-open="isOpen"
    :position="position"
    :header="exactDate"
    :items="menuItems"
    marker-attr="data-conversation-actions-menu"
    width-class="w-52"
    :width="208"
    :height="128"
    @select="handleSelect"
    @close="emit('close')"
  />
</template>

<script setup>
import FloatingActionMenu from '../../ui/FloatingActionMenu.vue'

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

const menuItems = [
  { id: 'rename', label: 'Rename', dividerBefore: true },
  { id: 'delete', label: 'Delete', destructive: true },
]

function handleSelect(action) {
  if (action === 'rename') emit('rename')
  else if (action === 'delete') emit('delete')
}
</script>
