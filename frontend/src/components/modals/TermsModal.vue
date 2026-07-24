<template>
  <Dialog :open="isOpen" @update:open="handleOpenChange">
    <DialogContent class="modal-card flex h-[min(600px,calc(100vh-2rem))] w-[calc(100vw-2rem)] max-w-2xl flex-col gap-0 overflow-hidden border-[var(--color-border)] bg-[var(--color-surface)] p-0">
          <!-- Modal Header -->
          <div class="modal-header shrink-0 flex items-center justify-between">
            <div class="flex items-center gap-3">
              <DocumentTextIcon class="h-5 w-5 shrink-0 text-[var(--color-accent)]" />
              <div>
                <DialogTitle class="text-base font-semibold text-[var(--color-text-main)]">Terms &amp; Conditions</DialogTitle>
                <DialogDescription class="sr-only">Read the current Inquira terms and conditions.</DialogDescription>
              </div>
            </div>
          </div>

          <!-- Modal Body -->
          <div class="flex-1 overflow-y-auto px-6 py-4 min-h-0 scrollbar-thin">
            <p v-if="termsLastUpdated" class="mb-4 text-xs text-[var(--color-text-muted)]">
              Last updated: {{ termsLastUpdated }}
            </p>
            <div
              class="rounded-xl border bg-[var(--color-base)] p-4 text-sm leading-6"
              style="border-color: var(--color-border);"
            >
              <p v-if="isTermsLoading" class="text-[var(--color-text-muted)]">Loading terms...</p>
              <p
                v-else-if="termsError"
                class="rounded-md border border-[var(--color-danger)]/35 bg-[var(--color-danger-bg)] px-3 py-2 text-xs text-[var(--color-danger-text)]"
              >
                {{ termsError }}
              </p>
              <div
                v-else
                class="terms-markdown-content"
                v-html="termsHtml"
              ></div>
            </div>
          </div>

          <!-- Modal Footer -->
          <DialogFooter class="modal-footer shrink-0 justify-end rounded-none border-t border-[var(--color-border)] bg-[var(--color-surface)] p-3">
            <DialogClose as-child>
              <Button class="btn-primary h-9 px-4 text-sm">Close</Button>
            </DialogClose>
          </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { DocumentTextIcon } from '@heroicons/vue/24/outline'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'
import { apiService } from '../../services/apiRuntime'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogTitle,
} from '@/components/ui/dialog'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close'])

const isTermsLoading = ref(false)
const termsError = ref('')
const termsMarkdown = ref('')
const termsLastUpdated = ref('')

const termsMarkdownRenderer = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
})

const termsHtml = computed(() => {
  const raw = String(termsMarkdown.value || '').trim()
  if (!raw) return ''
  return DOMPurify.sanitize(termsMarkdownRenderer.render(raw), {
    USE_PROFILES: { html: true },
  })
})

watch(
  () => props.isOpen,
  (isActive) => {
    if (isActive) {
      void loadTermsAndConditions()
    }
  },
  { immediate: true },
)

async function loadTermsAndConditions({ force = false } = {}) {
  if (termsMarkdown.value && !force) return
  isTermsLoading.value = true
  termsError.value = ''
  try {
    const payload = await apiService.v1GetTermsAndConditions() as unknown as {
      markdown?: string
      last_updated?: string
    }
    termsMarkdown.value = String(payload?.markdown || '').trim()
    termsLastUpdated.value = String(payload?.last_updated || '').trim()
  } catch (error: unknown) {
    termsError.value = error instanceof Error ? error.message : 'Failed to load Terms & Conditions.'
  } finally {
    isTermsLoading.value = false
  }
}

function handleOpenChange(open: boolean) {
  if (!open) emit('close')
}
</script>

<style scoped>
:deep(.terms-markdown-content h1),
:deep(.terms-markdown-content h2),
:deep(.terms-markdown-content h3) {
  margin-top: 1rem;
  margin-bottom: 0.5rem;
  font-weight: 700;
}

:deep(.terms-markdown-content h1:first-child),
:deep(.terms-markdown-content h2:first-child),
:deep(.terms-markdown-content h3:first-child) {
  margin-top: 0;
}

:deep(.terms-markdown-content p) {
  margin: 0.5rem 0;
}

:deep(.terms-markdown-content ul) {
  margin: 0.5rem 0;
  padding-left: 1.1rem;
  list-style: disc;
}

:deep(.terms-markdown-content li) {
  margin: 0.2rem 0;
}

:deep(.terms-markdown-content code) {
  background-color: color-mix(in srgb, var(--color-text-main) 10%, transparent);
  border-radius: 0.25rem;
  padding: 0.05rem 0.3rem;
}

:deep(.terms-markdown-content a) {
  color: var(--color-info);
  text-decoration: underline;
}
</style>
