<template>
  <Teleport to="body">
    <div
      v-if="isOpen"
      ref="menuRef"
      class="floating-action-menu layer-dropdown fixed overflow-hidden rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-elevated)] py-1 shadow-lg focus:outline-none"
      :class="widthClass"
      :style="menuStyle"
      tabindex="-1"
      data-floating-action-menu
      v-bind="markerAttributes"
      @click.stop
      @keydown.esc.stop.prevent="emit('close')"
    >
      <div
        v-if="header"
        class="px-3 py-2 text-[12px] font-medium text-[var(--color-text-muted)]"
        data-floating-action-menu-header
      >
        {{ header }}
      </div>
      <template v-for="item in normalizedItems" :key="item.id">
        <div
          v-if="item.dividerBefore"
          class="my-1 h-px bg-[var(--color-border)] opacity-70"
          data-floating-action-menu-divider
        />
        <button
          type="button"
          class="w-full px-3 py-1.5 text-left text-[12px] font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50"
          :class="item.destructive
            ? 'text-[var(--color-danger)] hover:bg-[var(--color-danger-bg)]'
            : 'text-[var(--color-text-main)] hover:bg-[var(--color-panel-muted)]'"
          :data-action-id="item.id"
          :disabled="item.disabled"
          @click.stop="handleSelect(item)"
        >
          {{ item.label }}
        </button>
      </template>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false,
  },
  position: {
    type: Object,
    default: () => ({ x: 0, y: 0 }),
  },
  items: {
    type: Array,
    default: () => [],
  },
  header: {
    type: String,
    default: '',
  },
  markerAttr: {
    type: String,
    default: '',
  },
  widthClass: {
    type: String,
    default: 'w-44',
  },
  width: {
    type: Number,
    default: 176,
  },
  height: {
    type: Number,
    default: 96,
  },
  clampPadding: {
    type: Number,
    default: 8,
  },
})

const emit = defineEmits(['select', 'close'])

const menuRef = ref(null)
const clampedPosition = ref({ x: 0, y: 0 })

const normalizedItems = computed(() => (
  Array.isArray(props.items)
    ? props.items
        .filter((item) => item && item.id && item.label)
        .map((item) => ({
          id: String(item.id),
          label: String(item.label),
          destructive: Boolean(item.destructive),
          dividerBefore: Boolean(item.dividerBefore),
          disabled: Boolean(item.disabled),
          closeOnSelect: item.closeOnSelect !== false,
        }))
    : []
))

const markerAttributes = computed(() => {
  const marker = String(props.markerAttr || '').trim()
  return marker ? { [marker]: '' } : {}
})

const menuStyle = computed(() => ({
  left: `${clampedPosition.value.x}px`,
  top: `${clampedPosition.value.y}px`,
}))

function resolveRawPosition() {
  return {
    x: Number(props.position?.x ?? props.position?.left ?? 0),
    y: Number(props.position?.y ?? props.position?.top ?? 0),
  }
}

function updateMenuPosition() {
  const gap = Number(props.clampPadding || 8)
  const rect = menuRef.value?.getBoundingClientRect?.()
  const width = Number(rect?.width || props.width || 176)
  const height = Number(rect?.height || props.height || 96)
  const viewportWidth = typeof window === 'undefined' ? width + gap * 2 : window.innerWidth
  const viewportHeight = typeof window === 'undefined' ? height + gap * 2 : window.innerHeight
  const raw = resolveRawPosition()
  clampedPosition.value = {
    x: Math.max(gap, Math.min(raw.x || gap, viewportWidth - width - gap)),
    y: Math.max(gap, Math.min(raw.y || gap, viewportHeight - height - gap)),
  }
}

function handleSelect(item) {
  if (item.disabled) return
  emit('select', item.id, item)
  if (item.closeOnSelect) emit('close')
}

function handleGlobalPointerDown(event) {
  if (!props.isOpen) return
  const target = event?.target
  if (!(target instanceof Element)) return
  if (menuRef.value?.contains(target)) return
  emit('close')
}

function handleViewportChange() {
  if (!props.isOpen) return
  updateMenuPosition()
}

watch(
  () => [props.isOpen, props.position?.x, props.position?.y, props.position?.left, props.position?.top, normalizedItems.value.length, props.header],
  async () => {
    if (!props.isOpen) return
    updateMenuPosition()
    await nextTick()
    updateMenuPosition()
  },
  { immediate: true },
)

watch(() => props.isOpen, (isOpen) => {
  if (!isOpen) return
  void nextTick(() => menuRef.value?.focus?.())
})

if (typeof document !== 'undefined') {
  document.addEventListener('pointerdown', handleGlobalPointerDown)
}
if (typeof window !== 'undefined') {
  window.addEventListener('resize', handleViewportChange)
  window.addEventListener('scroll', handleViewportChange, true)
}

onBeforeUnmount(() => {
  if (typeof document !== 'undefined') {
    document.removeEventListener('pointerdown', handleGlobalPointerDown)
  }
  if (typeof window !== 'undefined') {
    window.removeEventListener('resize', handleViewportChange)
    window.removeEventListener('scroll', handleViewportChange, true)
  }
})
</script>
