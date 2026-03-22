<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 overflow-y-auto bg-[radial-gradient(circle_at_top_left,_rgba(255,255,255,0.92),_rgba(244,239,223,0.96)_42%,_rgba(232,224,199,0.98))]"
  >
    <div class="min-h-screen p-4 sm:p-6 lg:p-8">
      <div class="mx-auto flex min-h-[calc(100vh-2rem)] max-w-7xl overflow-hidden rounded-[2rem] border border-stone-200/80 bg-[#f8f4e7] shadow-[0_24px_80px_rgba(41,37,36,0.18)] sm:min-h-[calc(100vh-3rem)]">
        <div class="relative flex w-full flex-col lg:flex-row">
          <section class="relative flex w-full items-center justify-center overflow-hidden border-b border-stone-200/70 bg-[#efe9d7] px-8 py-12 lg:w-[48%] lg:border-b-0 lg:border-r">
            <div class="absolute inset-0 opacity-70">
              <div class="absolute left-[-8%] top-[-6%] h-52 w-52 rounded-full bg-emerald-200/40 blur-3xl"></div>
              <div class="absolute bottom-10 right-0 h-48 w-48 rounded-full bg-amber-200/50 blur-3xl"></div>
            </div>

            <Transition name="auth-stage" mode="out-in">
              <div
                v-if="showProgressScreen"
                key="progress"
                class="relative z-10 mx-auto flex w-full max-w-xl flex-col gap-8"
              >
                <div class="space-y-4">
                  <div class="inline-flex items-center gap-3 rounded-full border border-emerald-900/10 bg-white/70 px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-emerald-900/70 shadow-sm backdrop-blur">
                    <span class="h-2.5 w-2.5 rounded-full bg-emerald-700 shadow-[0_0_0_5px_rgba(6,95,70,0.12)]"></span>
                    Inquira Session
                  </div>
                  <h1 class="max-w-md text-4xl font-semibold tracking-[-0.04em] text-stone-950 sm:text-5xl">
                    {{ progressHeading }}
                  </h1>
                  <p class="max-w-lg text-base leading-7 text-stone-600 sm:text-lg">
                    {{ progressLead }}
                  </p>
                </div>

                <div class="rounded-[1.75rem] border border-stone-200/80 bg-white/85 p-6 shadow-[0_20px_60px_rgba(120,113,108,0.14)] backdrop-blur">
                  <div class="flex items-center justify-between gap-4">
                    <div>
                      <p class="text-xs font-semibold uppercase tracking-[0.26em] text-stone-400">Current step</p>
                      <p class="mt-2 text-2xl font-semibold tracking-[-0.03em] text-stone-950">
                        {{ progressTitle }}
                      </p>
                    </div>
                    <div class="flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-950 text-sm font-semibold text-white shadow-lg">
                      {{ progressPercent }}%
                    </div>
                  </div>

                  <div class="mt-6 h-3 overflow-hidden rounded-full bg-stone-200">
                    <div
                      class="h-full rounded-full bg-[linear-gradient(90deg,#0f766e,#14532d)] transition-all duration-700 ease-out"
                      :style="{ width: `${progressPercent}%` }"
                    ></div>
                  </div>

                  <div class="mt-6 rounded-2xl bg-stone-950 px-4 py-4 text-stone-100 shadow-inner">
                    <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-emerald-200/80">
                      Live status
                    </p>
                    <div class="mt-3 min-h-[1.75rem] overflow-hidden">
                      <p
                        :key="authStore.authFlowStage"
                        class="auth-typewriter text-sm text-stone-100 sm:text-base"
                        :style="{ '--type-width': `${typingWidthCh}ch` }"
                      >
                        {{ typingMessage }}
                      </p>
                    </div>
                  </div>

                  <div class="mt-6 grid gap-3 sm:grid-cols-3">
                    <div
                      v-for="item in progressTimeline"
                      :key="item.title"
                      :class="[
                        'rounded-2xl border px-4 py-4 transition-all duration-300',
                        item.active
                          ? 'border-emerald-600 bg-emerald-50 text-emerald-950 shadow-sm'
                          : item.done
                            ? 'border-stone-200 bg-stone-50 text-stone-700'
                            : 'border-stone-200/80 bg-white text-stone-400',
                      ]"
                    >
                      <div class="flex items-center gap-2">
                        <span
                          :class="[
                            'h-2.5 w-2.5 rounded-full',
                            item.active ? 'bg-emerald-600' : item.done ? 'bg-stone-500' : 'bg-stone-300',
                          ]"
                        ></span>
                        <p class="text-sm font-medium">{{ item.title }}</p>
                      </div>
                      <p class="mt-2 text-xs leading-5 opacity-80">{{ item.caption }}</p>
                    </div>
                  </div>
                </div>
              </div>

              <div
                v-else
                key="signin"
                class="relative z-10 mx-auto flex w-full max-w-xl flex-col gap-8"
              >
                <div class="space-y-4">
                  <div class="inline-flex items-center gap-3 rounded-full border border-stone-900/10 bg-white/70 px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-stone-700 shadow-sm backdrop-blur">
                    <span class="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-950 text-xs font-bold text-white">I</span>
                    Inquira Desktop
                  </div>
                  <h1 class="max-w-md text-4xl font-semibold tracking-[-0.04em] text-stone-950 sm:text-5xl">
                    Sign in once and stay signed in.
                  </h1>
                  <p class="max-w-lg text-base leading-7 text-stone-600 sm:text-lg">
                    Start with Google. Inquira will keep reconnecting your session automatically every time the desktop app opens.
                  </p>
                </div>

                <div v-if="displayMessage" class="rounded-2xl border border-red-200 bg-red-50/90 px-4 py-4 text-red-800 shadow-sm">
                  <div class="flex items-start gap-3">
                    <ExclamationTriangleIcon class="mt-0.5 h-5 w-5 shrink-0 text-red-500" />
                    <div>
                      <p class="text-sm font-semibold">Sign-in could not be completed</p>
                      <p class="mt-1 text-sm leading-6">{{ displayMessage }}</p>
                    </div>
                  </div>
                </div>

                <div class="rounded-[1.75rem] border border-stone-200/80 bg-white/88 p-6 shadow-[0_20px_60px_rgba(120,113,108,0.14)] backdrop-blur">
                  <div class="space-y-4">
                    <button
                      @click="handleProviderSignIn('google')"
                      :disabled="authStore.isLoading"
                      class="group flex w-full items-center justify-between rounded-2xl border border-stone-200 bg-white px-5 py-4 text-left shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:border-emerald-700 hover:shadow-lg disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      <div class="flex items-center gap-4">
                        <div class="flex h-12 w-12 items-center justify-center rounded-2xl bg-stone-50 ring-1 ring-stone-200">
                          <span class="text-2xl font-semibold text-[#4285F4]">G</span>
                        </div>
                        <div>
                          <p class="text-base font-semibold text-stone-950">Continue with Google</p>
                          <p class="text-sm text-stone-500">Recommended for desktop sign-in</p>
                        </div>
                      </div>
                      <span class="text-sm font-medium text-emerald-800 transition-transform duration-200 group-hover:translate-x-1">
                        Open browser
                      </span>
                    </button>

                    <button
                      v-for="provider in comingSoonProviders"
                      :key="provider.id"
                      disabled
                      class="flex w-full items-center justify-between rounded-2xl border border-dashed border-stone-300 bg-stone-100/80 px-5 py-4 text-left opacity-75 disabled:cursor-not-allowed"
                    >
                      <div class="flex items-center gap-4">
                        <div class="flex h-12 w-12 items-center justify-center rounded-2xl bg-white text-sm font-semibold text-stone-500 ring-1 ring-stone-200">
                          {{ provider.badge }}
                        </div>
                        <div>
                          <p class="text-base font-semibold text-stone-700">{{ provider.label }}</p>
                          <p class="text-sm text-stone-500">Coming soon</p>
                        </div>
                      </div>
                      <span class="rounded-full border border-stone-300 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-stone-500">
                        Coming soon
                      </span>
                    </button>
                  </div>

                  <div class="mt-8 space-y-3 border-t border-stone-200 pt-6">
                    <p class="text-xs font-semibold uppercase tracking-[0.24em] text-stone-400">How it works</p>
                    <div class="grid gap-3 sm:grid-cols-3">
                      <div class="rounded-2xl bg-stone-50 px-4 py-4">
                        <p class="text-sm font-semibold text-stone-900">1. Browser login</p>
                        <p class="mt-2 text-xs leading-5 text-stone-500">Google opens in your browser for the secure sign-in step.</p>
                      </div>
                      <div class="rounded-2xl bg-stone-50 px-4 py-4">
                        <p class="text-sm font-semibold text-stone-900">2. Desktop verification</p>
                        <p class="mt-2 text-xs leading-5 text-stone-500">Inquira exchanges the code, restores the session, and verifies it locally.</p>
                      </div>
                      <div class="rounded-2xl bg-stone-50 px-4 py-4">
                        <p class="text-sm font-semibold text-stone-900">3. Auto reconnect</p>
                        <p class="mt-2 text-xs leading-5 text-stone-500">On later launches you should only see the reconnect screen, not the provider list.</p>
                      </div>
                    </div>
                  </div>

                  <p class="mt-6 text-xs leading-6 text-stone-500">
                    By continuing, you agree to the
                    <a
                      href="/terms-and-conditions.html"
                      @click.prevent="openTermsAndConditions"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="font-semibold text-emerald-800 underline decoration-emerald-300 underline-offset-4 hover:text-emerald-900"
                    >
                      Terms &amp; Conditions
                    </a>.
                  </p>
                </div>
              </div>
            </Transition>
          </section>

          <aside class="relative hidden overflow-hidden bg-[#fbf8ef] lg:flex lg:w-[52%] lg:flex-col lg:justify-between">
            <div class="absolute inset-0">
              <div class="absolute -left-16 top-10 h-52 w-52 rounded-full bg-amber-200/30 blur-3xl"></div>
              <div class="absolute bottom-10 right-16 h-64 w-64 rounded-full bg-emerald-100/50 blur-3xl"></div>
              <div class="absolute inset-x-16 bottom-0 h-[58%] rounded-t-[3rem] border border-stone-200/80 bg-[linear-gradient(180deg,rgba(255,255,255,0.62),rgba(240,234,214,0.92))]"></div>
            </div>

            <div class="relative z-10 px-12 pt-14">
              <div class="max-w-xl">
                <p class="text-xs font-semibold uppercase tracking-[0.28em] text-stone-400">Desktop onboarding</p>
                <h2 class="mt-4 text-5xl font-semibold tracking-[-0.045em] text-stone-950">
                  Calm startup, clear feedback, and a faster handoff from browser to app.
                </h2>
                <p class="mt-6 max-w-lg text-lg leading-8 text-stone-600">
                  Inquira should feel local the moment it opens. The auth screen now mirrors that: one focused sign-in path, then a dedicated progress page that tells you exactly what the app is doing.
                </p>
              </div>
            </div>

            <div class="relative z-10 px-12 pb-10">
              <div class="rounded-[2rem] border border-stone-200/80 bg-white/80 p-8 shadow-[0_16px_48px_rgba(120,113,108,0.12)] backdrop-blur">
                <div class="grid gap-6 md:grid-cols-[1.1fr_0.9fr]">
                  <div>
                    <p class="text-6xl leading-none text-amber-500">“</p>
                    <p class="mt-4 text-3xl font-semibold leading-[1.2] tracking-[-0.04em] text-stone-950">
                      Returning users should feel the app reconnecting, not wondering if it is stuck.
                    </p>
                    <div class="mt-8 flex items-center gap-4">
                      <div class="flex h-14 w-14 items-center justify-center rounded-full bg-stone-200 text-lg font-semibold text-stone-700">
                        I
                      </div>
                      <div>
                        <p class="text-lg font-semibold text-stone-900">Inquira Desktop</p>
                        <p class="text-sm text-stone-500">Local-first analytics workspace</p>
                      </div>
                    </div>
                  </div>

                  <div class="relative min-h-[22rem] overflow-hidden rounded-[1.75rem] border border-stone-200 bg-[linear-gradient(180deg,#f7f2e3,#fffdf7)]">
                    <div class="absolute left-8 top-8 h-24 w-16 rounded-[1.5rem] border-[6px] border-emerald-950/70 border-b-0"></div>
                    <div class="absolute bottom-0 left-6 h-40 w-16 rounded-t-[2rem] border-[6px] border-stone-700/65 border-b-0"></div>
                    <div class="absolute bottom-0 left-20 h-52 w-20 rounded-t-[2.5rem] border-[6px] border-stone-700/65 border-b-0"></div>
                    <div class="absolute bottom-0 left-40 h-36 w-16 rounded-t-[2rem] border-[6px] border-stone-700/65 border-b-0"></div>
                    <div class="absolute bottom-0 left-56 h-64 w-24 rounded-t-[2.75rem] border-[6px] border-stone-700/65 border-b-0"></div>
                    <div class="absolute bottom-0 right-8 h-44 w-20 rounded-t-[2rem] border-[6px] border-stone-700/65 border-b-0"></div>
                    <div class="absolute bottom-5 left-10 h-24 w-24 rounded-full border-[6px] border-stone-700/65"></div>
                    <div class="absolute bottom-8 right-14 h-20 w-20 rounded-full border-[6px] border-stone-700/65"></div>
                    <div class="absolute right-8 top-8 rounded-full bg-amber-100 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-amber-800">
                      Progress-first
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, watch } from 'vue'
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

const comingSoonProviders = [
  { id: 'azure', label: 'Continue with Microsoft', badge: 'MS' },
  { id: 'github', label: 'Continue with GitHub', badge: 'GH' },
]

const progressConfig = computed(() => {
  const stage = String(authStore.authFlowStage || '').trim()
  const fallback = authStore.authFlowMessage || ''

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
      return { percent: 0, title: '', description: '' }
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

const progressHeading = computed(() => {
  if (authStore.authFlowStage === 'restoring_session') {
    return 'Restoring your desktop session.'
  }
  return 'Finishing sign-in inside Inquira.'
})

const progressLead = computed(() => {
  if (authStore.authFlowStage === 'restoring_session') {
    return 'You should only see this reconnect screen briefly while Inquira restores your saved session and reattaches to the local backend.'
  }
  return 'The browser step is complete. Inquira is now exchanging credentials, verifying the session locally, and loading your account state.'
})

const typingMessage = computed(() => {
  return progressDescription.value || 'Preparing your Inquira session...'
})

const typingWidthCh = computed(() => {
  return Math.max(32, Math.min(96, typingMessage.value.length + 2))
})

const progressTimeline = computed(() => {
  const percent = progressPercent.value
  const stage = String(authStore.authFlowStage || '').trim()
  const isRestore = stage === 'restoring_session'
  return [
    {
      title: isRestore ? 'Restore session' : 'Browser handoff',
      caption: isRestore
        ? 'Load the saved desktop session from persistent storage.'
        : 'Receive the Google callback from your browser.',
      active: percent < 62,
      done: percent >= 62,
    },
    {
      title: 'Verify locally',
      caption: 'Wait for the local backend and verify the Supabase session.',
      active: percent >= 62 && percent < 96,
      done: percent >= 96,
    },
    {
      title: 'Load workspace',
      caption: 'Continue into the app once your account context is ready.',
      active: percent >= 96,
      done: false,
    },
  ]
})

function openTermsAndConditions() {
  void openExternalUrl('https://github.com/adarsh9780/inquira-ce/blob/main/frontend/public/terms-and-conditions.html')
}

async function handleProviderSignIn(provider) {
  await authStore.signInWithProvider(provider)
}

watch(
  () => props.isOpen,
  (isOpen) => {
    if (isOpen) {
      authStore.clearError()
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
.auth-stage-enter-active,
.auth-stage-leave-active {
  transition: opacity 280ms ease, transform 280ms ease;
}

.auth-stage-enter-from,
.auth-stage-leave-to {
  opacity: 0;
  transform: translateY(18px) scale(0.985);
}

.auth-typewriter {
  width: 0;
  overflow: hidden;
  white-space: nowrap;
  border-right: 2px solid rgba(167, 243, 208, 0.9);
  animation:
    auth-type 1.8s steps(30, end) forwards,
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
