<template>
  <Teleport to="body">
    <Transition name="motion-popover" @before-enter="prepareMenuEnter">
      <div
        v-if="isOpen"
        ref="menuRef"
        class="floating-action-menu motion-popover-surface layer-dropdown fixed overflow-hidden rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-elevated)] py-1 shadow-lg focus:outline-none"
        :class="widthClass"
        :style="menuStyle"
        tabindex="-1"
        role="menu"
        data-floating-action-menu
        v-bind="markerAttributes"
        @click.stop
        @keydown="handleMenuKeydown"
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
            :ref="(element) => setItemRef(element, item.id)"
            type="button"
            role="menuitem"
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
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'

interface MenuPosition {
  x?: number
  y?: number
  left?: number
  top?: number
}
interface MenuItem {
  id: string
  label: string
  destructive?: boolean
  dividerBefore?: boolean
  disabled?: boolean
  closeOnSelect?: boolean
}

const props = withDefaults(defineProps<{
  isOpen?: boolean
  position?: MenuPosition
  items?: MenuItem[]
  header?: string
  markerAttr?: string
  widthClass?: string
  width?: number
  height?: number
  clampPadding?: number
}>(), {
  isOpen: false,
  position: () => ({ x: 0, y: 0 }),
  items: () => [],
  header: '',
  markerAttr: '',
  widthClass: 'w-44',
  width: 176,
  height: 96,
  clampPadding: 8,
})

const emit = defineEmits<{
  select: [id: string, item: MenuItem]
  close: []
}>()

const menuRef = ref<HTMLElement | null>(null)
const itemRefs = ref(new Map<string, HTMLElement>())
const clampedPosition = ref({ x: 0, y: 0 })
let triggerElement: HTMLElement | null = null

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

function updateMenuPosition(element: HTMLElement | null = menuRef.value) {
  const gap = Number(props.clampPadding || 8)
  const rect = element?.getBoundingClientRect?.()
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

function prepareMenuEnter(element: Element) {
  if (!(element instanceof HTMLElement)) return
  updateMenuPosition(element)
  element.style.left = `${clampedPosition.value.x}px`
  element.style.top = `${clampedPosition.value.y}px`
}

function handleSelect(item: MenuItem) {
  if (item.disabled) return
  emit('select', item.id, item)
  if (item.closeOnSelect) emit('close')
}

function handleGlobalPointerDown(event: PointerEvent) {
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

function setItemRef(element: Element | { $el?: Element } | null, id: string) {
  const candidate = element instanceof Element ? element : element?.$el
  if (candidate instanceof HTMLElement) itemRefs.value.set(id, candidate)
  else itemRefs.value.delete(id)
}

function enabledItems(): HTMLElement[] {
  return normalizedItems.value
    .filter((item) => !item.disabled)
    .map((item) => itemRefs.value.get(item.id))
    .filter((item): item is HTMLElement => Boolean(item))
}

function handleMenuKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    event.stopPropagation()
    event.preventDefault()
    emit('close')
    return
  }
  const items = enabledItems()
  if (!items.length || !['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return
  event.preventDefault()
  const currentIndex = items.indexOf(document.activeElement as HTMLElement)
  if (event.key === 'Home') items[0]?.focus()
  else if (event.key === 'End') items.at(-1)?.focus()
  else if (event.key === 'ArrowDown') items[(currentIndex + 1 + items.length) % items.length]?.focus()
  else items[(currentIndex - 1 + items.length) % items.length]?.focus()
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
  if (isOpen) {
    triggerElement = document.activeElement instanceof HTMLElement ? document.activeElement : null
    void nextTick(() => enabledItems()[0]?.focus?.())
    return
  }
  triggerElement?.focus?.()
  triggerElement = null
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
