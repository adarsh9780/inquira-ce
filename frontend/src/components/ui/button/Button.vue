<script setup lang="ts">
import { Primitive, type PrimitiveProps } from 'reka-ui'
import { computed } from 'vue'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '../../../lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md font-semibold outline-none transition-[background-color,color,border-color,box-shadow,opacity] motion-fast focus-visible:ring-2 focus-visible:ring-[var(--color-focus-ring)] focus-visible:ring-offset-1 focus-visible:ring-offset-[var(--color-base)] disabled:pointer-events-none disabled:opacity-45',
  {
    variants: {
      variant: {
        primary: 'border border-transparent bg-[var(--color-accent)] text-[var(--color-accent-contrast)] hover:bg-[var(--color-accent-hover)]',
        secondary: 'border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-main)] hover:border-[var(--color-border-hover)] hover:bg-[var(--color-panel-muted)]',
        ghost: 'border border-transparent text-[var(--color-text-muted)] hover:bg-[var(--color-panel-muted)] hover:text-[var(--color-text-main)]',
        danger: 'border border-[var(--color-danger)]/35 bg-[var(--color-danger-bg)] text-[var(--color-danger-text)] hover:border-[var(--color-danger)]/60',
      },
      size: {
        sm: 'h-7 px-2.5 text-xs',
        md: 'h-8 px-3 text-[13px]',
        lg: 'h-9 px-4 text-sm',
        icon: 'h-8 w-8 p-0',
      },
    },
    defaultVariants: {
      variant: 'secondary',
      size: 'md',
    },
  },
)

type ButtonVariants = VariantProps<typeof buttonVariants>

const props = withDefaults(defineProps<PrimitiveProps & {
  variant?: ButtonVariants['variant']
  size?: ButtonVariants['size']
  class?: string
}>(), {
  as: 'button',
  variant: 'secondary',
  size: 'md',
})

const classes = computed(() => cn(buttonVariants({ variant: props.variant, size: props.size }), props.class))
</script>

<template>
  <Primitive :as="as" :as-child="asChild" :class="classes">
    <slot />
  </Primitive>
</template>
