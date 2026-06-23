<template>
  <div
    class="group/sidebar-conversation relative flex min-h-8 cursor-pointer select-none items-center rounded-md px-2 py-1.5 transition-colors hover:bg-[var(--color-text-main)]/5"
    :class="active ? 'bg-[var(--color-selected-surface)] text-[var(--color-text-main)]' : 'text-[var(--color-text-muted)]'"
    :title="conversationTitle"
    role="button"
    tabindex="0"
    @click="emit('select')"
    @contextmenu.prevent="emit('contextmenu', $event)"
    @keydown.enter.prevent="emit('select')"
    @keydown.space.prevent="emit('select')"
  >
    <div v-if="isEditing" class="flex w-full items-center gap-1" @click.stop>
      <input
        ref="editInputRef"
        :value="editingTitleValue"
        class="w-full rounded border border-[var(--color-accent)] bg-[var(--color-surface)] px-2 py-1 text-[14px] text-[var(--color-text-main)] outline-none"
        @input="emit('update:editingTitleValue', $event.target.value)"
        @keydown.stop
        @keydown.enter.prevent="emit('save-title')"
        @keydown.esc.prevent="emit('cancel-edit')"
        @blur="emit('save-title')"
      />
    </div>

    <template v-else>
      <p
        class="min-w-0 flex-1 truncate text-[13px] font-medium leading-snug"
        :class="active
          ? 'text-[var(--color-text-main)]'
          : 'text-[var(--color-text-muted)] group-hover/sidebar-conversation:text-[var(--color-text-main)]'"
        :title="conversationTitle"
      >
        {{ conversationTitle }}
      </p>
      <div class="relative ml-2 flex h-6 w-8 shrink-0 items-center justify-end">
        <span
          class="sidebar-conversation-time text-[12px] leading-none text-[var(--color-text-muted)] transition-opacity motion-fast"
          :class="menuOpen ? 'opacity-0' : 'opacity-100 group-hover/sidebar-conversation:opacity-0 group-focus-within/sidebar-conversation:opacity-0'"
        >
          {{ compactTimestamp }}
        </span>
        <button
          type="button"
          class="sidebar-conversation-action absolute right-0 flex h-6 w-6 items-center justify-center rounded-md text-[var(--color-text-muted)] transition-[opacity,background-color,color] motion-fast hover:bg-[var(--color-surface)] hover:text-[var(--color-text-main)] focus:outline-none"
          :class="menuOpen
            ? 'pointer-events-auto opacity-100'
            : 'pointer-events-none opacity-0 group-hover/sidebar-conversation:pointer-events-auto group-hover/sidebar-conversation:opacity-100 group-focus-within/sidebar-conversation:pointer-events-auto group-focus-within/sidebar-conversation:opacity-100'"
          title="Conversation actions"
          aria-label="Conversation actions"
          @click.stop="emit('toggle-menu', $event)"
          @keydown.enter.stop
          @keydown.space.stop
        >
          <EllipsisHorizontalIcon class="h-4 w-4" />
        </button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { EllipsisHorizontalIcon } from '@heroicons/vue/24/outline'

const props = defineProps({
  conversation: {
    type: Object,
    required: true,
  },
  active: {
    type: Boolean,
    default: false,
  },
  isEditing: {
    type: Boolean,
    default: false,
  },
  editingTitleValue: {
    type: String,
    default: '',
  },
  compactTimestamp: {
    type: String,
    default: '',
  },
  menuOpen: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits([
  'select',
  'contextmenu',
  'toggle-menu',
  'update:editingTitleValue',
  'save-title',
  'cancel-edit',
])

const editInputRef = ref(null)

const conversationTitle = computed(() => (
  String(props.conversation?.title || '').trim() || 'Untitled'
))

watch(() => props.isEditing, async (isEditing) => {
  if (!isEditing) return
  await nextTick()
  editInputRef.value?.focus?.()
  editInputRef.value?.select?.()
})
</script>
