<template>
  <div class="rounded-xl border p-3 space-y-3" style="border-color: color-mix(in srgb, var(--color-border) 70%, #f59e0b 30%); background-color: color-mix(in srgb, var(--color-surface) 92%, #fef3c7 8%);">
    <p class="text-xs font-semibold uppercase tracking-[0.08em]" style="color: var(--color-text-muted);">
      Agent needs your input
    </p>
    <p class="text-sm" style="color: var(--color-text-main);">
      {{ prompt }}
    </p>

    <div v-if="options.length" class="space-y-1">
      <label
        v-for="item in options"
        :key="item"
        class="flex items-center gap-2 text-sm"
        style="color: var(--color-text-main);"
      >
        <input
          :type="multiSelect ? 'checkbox' : 'radio'"
          :name="radioName"
          :checked="isSelected(item)"
          @change="toggleSelection(item)"
        />
        <span>{{ item }}</span>
      </label>
    </div>

    <div class="flex items-center gap-2">
      <button
        type="button"
        class="px-3 py-1.5 rounded text-xs font-medium border"
        style="border-color: var(--color-border); color: var(--color-text-main);"
        :disabled="busy || status !== 'pending'"
        @click="submitSelection"
      >
        Approve
      </button>
      <button
        type="button"
        class="px-3 py-1.5 rounded text-xs font-medium border"
        style="border-color: var(--color-border); color: var(--color-text-muted);"
        :disabled="busy || status !== 'pending'"
        @click="denySelection"
      >
        Deny
      </button>
      <span v-if="status !== 'pending'" class="text-xs" style="color: var(--color-text-muted);">
        {{ status }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  intervention: {
    type: Object,
    required: true,
  },
  busy: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['respond'])
const selected = ref([])

const prompt = computed(() => String(props.intervention?.prompt || ''))
const options = computed(() => {
  const list = props.intervention?.options
  return Array.isArray(list) ? list.map((item) => String(item || '')).filter(Boolean) : []
})
const multiSelect = computed(() => Boolean(props.intervention?.multi_select))
const status = computed(() => String(props.intervention?.status || 'pending'))
const radioName = computed(() => `intervention-${String(props.intervention?.id || '')}`)

watch(
  () => props.intervention?.id,
  () => {
    const initial = Array.isArray(props.intervention?.selected) ? props.intervention.selected : []
    selected.value = initial.map((item) => String(item || ''))
  },
  { immediate: true }
)

function isSelected(item) {
  return selected.value.includes(String(item))
}

function toggleSelection(item) {
  const key = String(item)
  if (!multiSelect.value) {
    selected.value = [key]
    return
  }
  if (selected.value.includes(key)) {
    selected.value = selected.value.filter((value) => value !== key)
  } else {
    selected.value = [...selected.value, key]
  }
}

function submitSelection() {
  emit('respond', {
    id: String(props.intervention?.id || ''),
    selected: [...selected.value],
  })
}

function denySelection() {
  emit('respond', {
    id: String(props.intervention?.id || ''),
    selected: [],
  })
}
</script>
