<template>
  <div
    v-if="items.length > 0"
    class="absolute left-0 right-0 z-[70] max-h-56 w-full overflow-y-auto rounded-xl border shadow-lg"
    :class="openUp ? 'bottom-full mb-2' : 'top-full mt-1'"
    style="background-color: var(--color-base); border-color: var(--color-border);"
  >
    <ul class="py-1">
      <li
        v-for="(item, index) in items"
        :key="`${item.table_name}.${item.column_name}:${index}`"
      >
        <button
          type="button"
          class="flex w-full items-center justify-between px-3 py-2 text-left text-sm transition-colors"
          :class="index === selectedIndex ? 'bg-black/[0.05]' : 'hover:bg-black/[0.03]'"
          @mousedown.prevent="$emit('select', item)"
        >
          <span
            class="truncate"
            :style="item?.isSpecial ? 'color: #0284c7;' : 'color: var(--color-text-main);'"
          >
            {{ item.displayText || `${item.table_name}.${item.column_name}` }}
          </span>
          <span class="ml-2 rounded border px-1.5 py-0.5 text-[10px] uppercase" style="color: var(--color-text-muted); border-color: var(--color-border);">
            {{ item.dtype || 'UNKNOWN' }}
          </span>
        </button>
      </li>
    </ul>
  </div>
</template>

<script setup>
defineProps({
  items: {
    type: Array,
    default: () => [],
  },
  selectedIndex: {
    type: Number,
    default: 0,
  },
  openUp: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['select'])
</script>
