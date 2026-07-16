<template>
  <Transition
    enter-active-class="dialog-fade-enter-active dialog-pop-enter-active"
    enter-from-class="dialog-fade-enter-from dialog-pop-enter-from"
    leave-active-class="dialog-fade-leave-active dialog-pop-leave-active"
    leave-to-class="dialog-fade-leave-to dialog-pop-leave-to"
  >
    <!-- Modal Overlay -->
    <div
      v-if="isOpen"
      class="fixed inset-0 layer-modal overflow-y-auto"
      aria-labelledby="modal-title"
      role="dialog"
      aria-modal="true"
    >
      <!-- Background overlay -->
      <div
        class="modal-overlay"
        @click="closeModal"
      ></div>

      <!-- Modal container -->
      <div class="flex min-h-full items-center justify-center p-4 text-center sm:p-0">
        <div
          class="modal-card relative w-full max-w-2xl text-left sm:my-8 h-[600px] flex flex-col"
          @click.stop
        >
          <!-- Modal Header -->
          <div class="modal-header shrink-0 flex items-center justify-between">
            <div class="flex items-center gap-3">
              <DocumentTextIcon class="h-5 w-5 shrink-0 text-[var(--color-accent)]" />
              <h3 class="text-base font-semibold text-[var(--color-text-main)]" id="modal-title">Terms &amp; Conditions</h3>
            </div>
            <button
              type="button"
              class="btn-icon"
              aria-label="Close terms"
              @click="closeModal"
            >
              <svg viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="1.8">
                <path d="M6 6l12 12M18 6L6 18" />
              </svg>
            </button>
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
          <div class="modal-footer shrink-0 justify-end">
            <button @click="closeModal" class="btn-primary text-sm px-4 py-2">Close</button>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { DocumentTextIcon } from '@heroicons/vue/24/outline'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'
import { apiService } from '../../services/apiService'

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
    const payload = await apiService.v1GetTermsAndConditions()
    termsMarkdown.value = String(payload?.markdown || '').trim()
    termsLastUpdated.value = String(payload?.last_updated || '').trim()
  } catch (error) {
    termsError.value = error?.message || 'Failed to load Terms & Conditions.'
  } finally {
    isTermsLoading.value = false
  }
}

function closeModal() {
  emit('close')
}

function handleEscape(e) {
  if (e.key === 'Escape' && props.isOpen) {
    closeModal()
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleEscape)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleEscape)
})
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
