<template>
  <section>
    <button
      type="button"
      class="sidebar-disclosure-button"
      :aria-expanded="open"
      @click="emit('update:open', !open)"
    >
      <ChevronRightIcon class="h-3.5 w-3.5 transition-transform" :class="open ? 'rotate-90' : ''" aria-hidden="true" />
      <span>{{ label }}</span>
    </button>
    <div class="motion-disclosure" :class="open ? 'motion-disclosure-open' : ''" :aria-hidden="!open">
      <div class="motion-disclosure-content"><slot /></div>
    </div>
  </section>
</template>

<script setup>
import { ChevronRightIcon } from '@heroicons/vue/24/outline'
defineProps({
  open: { type: Boolean, default: false },
  label: { type: String, required: true },
})
const emit = defineEmits(['update:open'])
</script>
