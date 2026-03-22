<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 overflow-y-auto bg-[#f6f2e8]"
  >
    <div class="relative min-h-screen overflow-hidden px-6 py-10">
      <div class="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.9),_rgba(246,242,232,0.98)_56%)]"></div>
      <div class="absolute left-1/2 top-16 h-72 w-72 -translate-x-1/2 rounded-full bg-white/70 blur-3xl"></div>

      <div class="relative mx-auto flex min-h-[calc(100vh-5rem)] max-w-6xl flex-col">
        <header class="pt-8 text-center">
          <p class="font-serif text-5xl italic tracking-[-0.04em] text-stone-900">Inquira</p>
          <p class="mt-2 font-serif text-lg italic text-stone-500">The Digital Curator</p>
        </header>

        <main class="flex flex-1 items-center justify-center py-10">
          <Transition name="auth-shell" mode="out-in">
            <section
              v-if="showProgressScreen"
              key="progress"
              class="w-full max-w-xl rounded-[2rem] border border-stone-200/80 bg-white/88 px-8 py-9 shadow-[0_30px_80px_rgba(120,113,108,0.16)] backdrop-blur"
            >
              <div class="space-y-3">
                <p class="text-xs font-semibold uppercase tracking-[0.26em] text-stone-400">Inquira startup</p>
                <h1 class="font-serif text-5xl tracking-[-0.04em] text-stone-900">
                  {{ progressHeading }}
                </h1>
                <p class="max-w-lg text-lg leading-8 text-stone-600">
                  {{ progressLead }}
                </p>
              </div>

              <div class="mt-8 rounded-[1.6rem] bg-[#f7f3ea] p-5">
                <div class="flex items-center justify-between gap-4">
                  <div>
                    <p class="text-xs font-semibold uppercase tracking-[0.24em] text-stone-400">Current step</p>
                    <p class="mt-2 text-2xl font-semibold tracking-[-0.03em] text-stone-900">
                      {{ progressTitle }}
                    </p>
                  </div>
                  <div class="rounded-full bg-stone-900 px-4 py-2 text-sm font-semibold text-white">
                    {{ progressPercent }}%
                  </div>
                </div>

                <div class="mt-5 h-3 overflow-hidden rounded-full bg-stone-200">
                  <div
                    class="h-full rounded-full bg-[linear-gradient(90deg,#57534e,#1c1917)] transition-all duration-700 ease-out"
                    :style="{ width: `${progressPercent}%` }"
                  ></div>
                </div>

                <div class="mt-5 rounded-[1.25rem] bg-white px-4 py-4 shadow-sm">
                  <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-stone-400">Live status</p>
                  <p
                    :key="authStore.authFlowStage"
                    class="auth-status-type mt-3 min-h-[1.75rem] text-sm text-stone-700"
                    :style="{ '--type-width': `${statusWidthCh}ch` }"
                  >
                    {{ progressDescription }}
                  </p>
                </div>
              </div>

              <div class="mt-8 grid gap-3 sm:grid-cols-3">
                <div
                  v-for="item in progressTimeline"
                  :key="item.title"
                  :class="[
                    'rounded-[1.25rem] border px-4 py-4 transition-all duration-300',
                    item.active
                      ? 'border-stone-900 bg-stone-900 text-white'
                      : item.done
                        ? 'border-stone-300 bg-stone-100 text-stone-700'
                        : 'border-stone-200 bg-white text-stone-400',
                  ]"
                >
                  <p class="text-sm font-semibold">{{ item.title }}</p>
                  <p class="mt-2 text-xs leading-5 opacity-80">{{ item.caption }}</p>
                </div>
              </div>
            </section>

            <section
              v-else
              key="signin"
              class="w-full max-w-xl rounded-[2rem] border border-stone-200/80 bg-white/90 px-8 py-9 shadow-[0_30px_80px_rgba(120,113,108,0.16)] backdrop-blur"
            >
              <div class="space-y-3">
                <h1 class="font-serif text-5xl tracking-[-0.04em] text-stone-900">Sign in</h1>
                <p class="max-w-lg text-lg leading-8 text-stone-600">
                  Welcome back. Sign in with Google to access your workspace.
                </p>
                <div class="min-h-[2rem] pt-2">
                  <p
                    :key="featureIndex"
                    class="auth-feature-type font-serif text-xl italic text-stone-500"
                    :style="{ '--type-width': `${featureWidthCh}ch` }"
                  >
                    {{ activeFeatureLine }}
                  </p>
                </div>
              </div>

              <div v-if="displayMessage" class="mt-6 rounded-[1.25rem] border border-red-200 bg-red-50 px-4 py-4 text-red-800 shadow-sm">
                <div class="flex items-start gap-3">
                  <ExclamationTriangleIcon class="mt-0.5 h-5 w-5 shrink-0 text-red-500" />
                  <div>
                    <p class="text-sm font-semibold">Sign-in could not be completed</p>
                    <p class="mt-1 text-sm leading-6">{{ displayMessage }}</p>
                  </div>
                </div>
              </div>

              <div class="mt-8 space-y-4">
                <button
                  @click="handleProviderSignIn('google')"
                  :disabled="authStore.isLoading"
                  class="flex w-full items-center justify-between rounded-[1.15rem] bg-[#666362] px-5 py-4 text-left text-white transition-all duration-200 hover:bg-[#55514f] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <div class="flex items-center gap-4">
                    <div class="flex h-11 w-11 items-center justify-center rounded-full bg-white text-lg font-semibold text-[#4285F4]">
                      G
                    </div>
                    <div>
                      <p class="text-lg font-semibold">Continue</p>
                      <p class="text-sm text-stone-200">Sign in with Google</p>
                    </div>
                  </div>
                  <span class="text-2xl leading-none">→</span>
                </button>

                <div class="flex items-center gap-4 py-1">
                  <div class="h-px flex-1 bg-stone-200"></div>
                  <span class="text-xs font-semibold uppercase tracking-[0.22em] text-stone-400">Or</span>
                  <div class="h-px flex-1 bg-stone-200"></div>
                </div>

                <div class="grid gap-3 sm:grid-cols-2">
                  <button
                    v-for="provider in comingSoonProviders"
                    :key="provider.id"
                    disabled
                    class="flex items-center justify-between rounded-[1.15rem] border border-stone-200 bg-[#f4f0e6] px-4 py-4 text-left text-stone-500 disabled:cursor-not-allowed"
                  >
                    <div class="flex items-center gap-3">
                      <div class="flex h-9 w-9 items-center justify-center rounded-full bg-white text-xs font-semibold text-stone-500">
                        {{ provider.badge }}
                      </div>
                      <div>
                        <p class="text-sm font-semibold text-stone-700">{{ provider.short }}</p>
                        <p class="text-xs text-stone-400">Coming soon</p>
                      </div>
                    </div>
                    <span class="text-xs font-semibold uppercase tracking-[0.18em] text-stone-400">Soon</span>
                  </button>
                </div>
              </div>
            </section>
          </Transition>
        </main>

        <footer class="pb-3 pt-6 text-center text-sm text-stone-400">
          <div class="flex flex-col items-center justify-between gap-4 sm:flex-row">
            <p class="font-serif text-2xl italic text-stone-500">Inquira</p>
            <div class="flex flex-wrap items-center justify-center gap-6 uppercase tracking-[0.18em]">
              <a
                href="/terms-and-conditions.html"
                @click.prevent="openTermsAndConditions"
                class="transition-colors hover:text-stone-700"
              >
                Terms of Service
              </a>
              <span>Privacy Policy</span>
              <span>Help Center</span>
            </div>
            <p>© 2026 Inquira</p>
          </div>
        </footer>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useAuthStore } from '../../stores/authStore'
import { openExternalUrl } from '../../services/externalLinkService'
import { ExclamationTriangleIcon } from '@heroicons/vue/24/outline'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['close'])

const authStore = useAuthStore()
const featureIndex = ref(0)
let featureTimer = null

const featureLines = [
  'Talk to your data in natural language.',
  'Run notebook-style analysis in one workspace.',
  'Switch between chat, code, tables, and charts.',
  'Keep desktop sessions warm between launches.',
]

const comingSoonProviders = [
  { id: 'azure', short: 'Microsoft', badge: 'MS' },
  { id: 'github', short: 'GitHub', badge: 'GH' },
]

const progressConfig = computed(() => {
  const stage = String(authStore.authFlowStage || '').trim()
  const fallback = authStore.authFlowMessage || 'Preparing your Inquira session...'

  switch (stage) {
    case 'browser_opening':
      return { percent: 18, title: 'Opening browser', description: fallback }
    case 'browser_wait':
      return { percent: 28, title: 'Waiting for browser sign-in', description: fallback }
    case 'browser_complete':
      return { percent: 46, title: 'Browser step completed', description: fallback }
    case 'exchanging_code':
      return { percent: 62, title: 'Exchanging sign-in code', description: fallback }
    case 'session_ready':
      return { percent: 76, title: 'Session received', description: fallback }
    case 'restoring_session':
      return { percent: 64, title: 'Restoring saved session', description: fallback }
    case 'verifying_session':
      return { percent: 84, title: 'Verifying session', description: fallback }
    case 'loading_account':
      return { percent: 96, title: 'Loading your account', description: fallback }
    default:
      return { percent: 0, title: '', description: fallback }
  }
})

const showProgressScreen = computed(() => {
  const stage = String(authStore.authFlowStage || '').trim()
  return !!stage && stage !== 'failed'
})

const progressPercent = computed(() => progressConfig.value.percent)
const progressTitle = computed(() => progressConfig.value.title)
const progressDescription = computed(() => progressConfig.value.description)
const displayMessage = computed(() => authStore.error || '')
const activeFeatureLine = computed(() => featureLines[featureIndex.value] || '')
const featureWidthCh = computed(() => Math.max(28, Math.min(72, activeFeatureLine.value.length + 2)))
const statusWidthCh = computed(() => Math.max(28, Math.min(80, progressDescription.value.length + 2)))

const progressHeading = computed(() => {
  if (authStore.authFlowStage === 'restoring_session') {
    return 'Welcome back'
  }
  return 'Almost there'
})

const progressLead = computed(() => {
  if (authStore.authFlowStage === 'restoring_session') {
    return 'Inquira found a saved session and is reconnecting your workspace.'
  }
  return 'The browser step is complete. Inquira is finishing the secure handoff inside the app.'
})

const progressTimeline = computed(() => {
  const percent = progressPercent.value
  const stage = String(authStore.authFlowStage || '').trim()
  const isRestore = stage === 'restoring_session'
  return [
    {
      title: isRestore ? 'Restore session' : 'Browser handoff',
      caption: isRestore ? 'Load the saved session from desktop storage.' : 'Receive the Google callback locally.',
      active: percent < 62,
      done: percent >= 62,
    },
    {
      title: 'Verify locally',
      caption: 'Wait for the backend and validate the session.',
      active: percent >= 62 && percent < 96,
      done: percent >= 96,
    },
    {
      title: 'Load workspace',
      caption: 'Continue into the app when the account context is ready.',
      active: percent >= 96,
      done: false,
    },
  ]
})

function startFeatureRotation() {
  stopFeatureRotation()
  featureTimer = window.setInterval(() => {
    featureIndex.value = (featureIndex.value + 1) % featureLines.length
  }, 2600)
}

function stopFeatureRotation() {
  if (featureTimer) {
    window.clearInterval(featureTimer)
    featureTimer = null
  }
}

function openTermsAndConditions() {
  void openExternalUrl('https://github.com/adarsh9780/inquira-ce/blob/main/frontend/public/terms-and-conditions.html')
}

async function handleProviderSignIn(provider) {
  await authStore.signInWithProvider(provider)
}

onMounted(() => {
  startFeatureRotation()
})

onBeforeUnmount(() => {
  stopFeatureRotation()
})

watch(
  () => props.isOpen,
  (isOpen) => {
    if (isOpen) {
      authStore.clearError()
      startFeatureRotation()
    } else {
      stopFeatureRotation()
    }
  },
)

watch(
  () => authStore.isAuthenticated,
  (isAuthenticated) => {
    if (isAuthenticated && props.isOpen) {
      emit('close')
    }
  },
)
</script>

<style scoped>
.auth-shell-enter-active,
.auth-shell-leave-active {
  transition: opacity 260ms ease, transform 260ms ease;
}

.auth-shell-enter-from,
.auth-shell-leave-to {
  opacity: 0;
  transform: translateY(14px);
}

.auth-feature-type,
.auth-status-type {
  width: 0;
  overflow: hidden;
  white-space: nowrap;
  border-right: 2px solid rgba(87, 83, 78, 0.7);
  animation:
    auth-type 1.4s steps(28, end) forwards,
    auth-caret 0.9s step-end infinite;
}

@keyframes auth-type {
  from {
    width: 0;
  }
  to {
    width: var(--type-width);
  }
}

@keyframes auth-caret {
  50% {
    border-color: transparent;
  }
}
</style>
