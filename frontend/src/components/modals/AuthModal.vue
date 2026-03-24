<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 overflow-y-auto bg-[var(--color-base)]"
  >
    <div class="relative min-h-screen overflow-hidden px-4 py-6 sm:px-6 lg:px-8">
      <div class="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(59,130,246,0.08),_transparent_30%),radial-gradient(circle_at_bottom_right,_rgba(24,24,27,0.08),_transparent_34%)]"></div>
      <div class="absolute inset-x-0 top-0 h-64 bg-[linear-gradient(180deg,rgba(255,255,255,0.92),rgba(253,252,248,0))]"></div>

      <div class="relative mx-auto flex min-h-[calc(100vh-3rem)] max-w-7xl flex-col">
        <main class="flex flex-1 items-center justify-center">
          <section
            class="w-full overflow-hidden rounded-[2rem] border border-[var(--color-border)] bg-white/88 shadow-[0_28px_90px_rgba(24,24,27,0.1)] backdrop-blur-xl"
          >
            <div class="grid min-h-[700px] lg:grid-cols-[1.12fr_0.88fr]">
              <aside class="auth-brand-panel relative overflow-hidden border-b border-[var(--color-border)] px-6 py-8 sm:px-8 lg:border-b-0 lg:border-r lg:px-10 lg:py-10">
                  <div class="auth-grid absolute inset-0 opacity-70"></div>
                  <div class="auth-glow absolute -left-16 top-10 h-48 w-48 rounded-full"></div>
                  <div class="auth-glow auth-glow-secondary absolute bottom-12 right-[-3rem] h-56 w-56 rounded-full"></div>

                <div class="relative flex h-full flex-col">
                  <div class="flex items-center gap-4">
                    <div class="flex h-14 w-14 items-center justify-center rounded-2xl border border-white/70 bg-white/90 shadow-[0_16px_32px_rgba(24,24,27,0.08)]">
                      <img :src="logo" alt="Inquira logo" class="h-10 w-10 rounded-xl shadow-sm" />
                    </div>

                    <div>
                      <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-[var(--color-text-muted)]">Inquira</p>
                      <p class="mt-1 text-sm text-[var(--color-text-muted)]">{{ heroPill }}</p>
                    </div>
                  </div>

                  <div class="mt-10 max-w-xl">
                    <p class="text-xs font-semibold uppercase tracking-[0.3em] text-[var(--color-text-muted)]">
                      {{ heroEyebrow }}
                    </p>
                    <h1 class="mt-4 text-4xl font-semibold tracking-[-0.05em] text-[var(--color-text-main)] sm:text-5xl lg:text-[3.6rem] lg:leading-[1.02]">
                      {{ heroTitle }}
                    </h1>
                    <p class="mt-5 max-w-lg text-base leading-7 text-[var(--color-text-muted)] sm:text-lg sm:leading-8">
                      {{ heroDescription }}
                    </p>
                  </div>

                  <div class="mt-8 rounded-[1.5rem] border border-white/70 bg-white/75 p-5 shadow-[0_20px_45px_rgba(24,24,27,0.08)]">
                    <div class="flex items-center justify-between gap-4">
                      <div>
                        <p class="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--color-text-muted)]">
                          {{ primaryPanelEyebrow }}
                        </p>
                        <p
                          v-if="showProgressScreen"
                          class="auth-status-type mt-3 min-h-[1.75rem] text-base text-[var(--color-text-main)] sm:text-lg"
                          :style="{ '--type-width': `${progressWidthCh}ch` }"
                        >
                          {{ progressTitle || 'Preparing your workspace' }}
                        </p>
                        <p
                          v-else
                          :key="featureIndex"
                          class="auth-feature-type mt-3 min-h-[1.75rem] text-base text-[var(--color-text-main)] sm:text-lg"
                          :style="{ '--type-width': `${featureWidthCh}ch` }"
                        >
                          {{ activeFeatureLine }}
                        </p>
                      </div>
                      <div class="hidden h-12 w-12 items-center justify-center rounded-full border border-[var(--color-border)] bg-white text-sm font-semibold text-[var(--color-text-main)] sm:flex">
                        {{ primaryPanelBadge }}
                      </div>
                    </div>
                  </div>

                  <ul class="mt-8 grid gap-3 text-sm sm:grid-cols-3 lg:mt-auto lg:grid-cols-1 xl:grid-cols-3">
                    <li
                      v-for="bullet in activeBrandBullets"
                      :key="bullet.title"
                      class="rounded-[1.35rem] border border-white/75 bg-white/72 px-4 py-4 shadow-[0_14px_30px_rgba(24,24,27,0.06)]"
                    >
                      <p class="text-sm font-semibold text-[var(--color-text-main)]">{{ bullet.title }}</p>
                      <p class="mt-2 text-sm leading-6 text-[var(--color-text-muted)]">{{ bullet.body }}</p>
                    </li>
                  </ul>
                </div>
              </aside>

              <div class="flex items-center px-6 py-8 sm:px-8 lg:px-10 lg:py-10">
                <div v-if="showProgressScreen" class="w-full">
                  <div class="mx-auto max-w-lg rounded-[1.75rem] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-[0_18px_48px_rgba(24,24,27,0.08)] sm:p-8">
                    <p class="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--color-text-muted)]">Inquira startup</p>
                    <h2 class="mt-4 text-3xl tracking-[-0.04em] text-[var(--color-text-main)] sm:text-4xl">
                      {{ progressTitle || 'Preparing your workspace' }}
                    </h2>
                    <p class="mt-4 text-base leading-7 text-[var(--color-text-muted)]">
                      {{ progressDescription }}
                    </p>

                    <div class="mt-8 rounded-[1.4rem] border border-zinc-200 bg-[var(--color-base)] p-5">
                      <div class="flex items-center gap-4">
                        <div class="auth-spinner" aria-hidden="true"></div>
                        <div>
                          <p class="text-sm font-semibold text-[var(--color-text-main)]">Completing secure sign-in</p>
                          <p class="mt-1 text-sm leading-6 text-[var(--color-text-muted)]">
                            This screen stays in place while Inquira verifies your session and restores your workspace.
                          </p>
                        </div>
                      </div>
                    </div>

                    <div class="mt-4 rounded-[1.4rem] border border-zinc-200 bg-white px-4 py-4">
                      <div class="flex items-center justify-between gap-4">
                        <div>
                          <p class="text-xs font-semibold uppercase tracking-[0.22em] text-[var(--color-text-muted)]">Current step</p>
                          <p class="mt-2 text-base font-medium text-[var(--color-text-main)]">{{ progressTitle || 'Preparing your workspace' }}</p>
                        </div>
                        <span class="rounded-full border border-zinc-200 bg-[var(--color-base)] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--color-text-muted)]">
                          {{ progressPercentLabel }}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                <div v-else class="w-full">
                  <div class="mx-auto max-w-lg">
                    <div class="rounded-[1.75rem] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-[0_18px_48px_rgba(24,24,27,0.08)] sm:p-8">
                      <p class="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--color-text-muted)]">Sign in to continue</p>
                      <h2 class="mt-4 text-3xl tracking-[-0.04em] text-[var(--color-text-main)] sm:text-4xl">Welcome back</h2>
                      <p class="mt-4 text-base leading-7 text-[var(--color-text-muted)]">
                        Welcome back. Sign in with Google to access your workspace. Microsoft and GitHub login are planned next.
                      </p>

                      <div v-if="displayMessage" class="mt-6 rounded-[1.25rem] border border-red-200 bg-red-50 px-4 py-4 text-red-800 shadow-sm">
                        <div class="flex items-start gap-3">
                          <ExclamationTriangleIcon class="mt-0.5 h-5 w-5 shrink-0 text-red-500" />
                          <div>
                            <p class="text-sm font-semibold text-red-800">Sign-in could not be completed</p>
                            <p class="mt-1 text-sm leading-6 text-red-700">{{ displayMessage }}</p>
                          </div>
                        </div>
                      </div>

                      <div class="mt-8 space-y-4">
                        <button
                          @click="handleProviderSignIn('google')"
                          :disabled="authStore.isLoading"
                          class="group flex w-full items-center justify-between rounded-[1.25rem] border border-zinc-900 bg-zinc-900 px-5 py-4 text-left text-white transition-all duration-200 hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          <div class="flex items-center gap-4">
                            <div class="flex h-12 w-12 items-center justify-center rounded-full bg-white shadow-sm">
                              <svg viewBox="0 0 48 48" class="h-6 w-6" aria-hidden="true">
                                <path fill="#FFC107" d="M43.611 20.083H42V20H24v8h11.303C33.654 32.657 29.243 36 24 36c-6.627 0-12-5.373-12-12s5.373-12 12-12c3.059 0 5.842 1.154 7.959 3.041l5.657-5.657C34.046 6.053 29.277 4 24 4 12.955 4 4 12.955 4 24s8.955 20 20 20 20-8.955 20-20c0-1.341-.138-2.651-.389-3.917Z"/>
                                <path fill="#FF3D00" d="M6.306 14.691l6.571 4.819C14.655 15.108 18.961 12 24 12c3.059 0 5.842 1.154 7.959 3.041l5.657-5.657C34.046 6.053 29.277 4 24 4c-7.682 0-14.347 4.337-17.694 10.691Z"/>
                                <path fill="#4CAF50" d="M24 44c5.176 0 9.86-1.977 13.409-5.192l-6.19-5.238C29.143 35.091 26.715 36 24 36c-5.222 0-9.618-3.317-11.283-7.946l-6.522 5.025C9.5 39.556 16.227 44 24 44Z"/>
                                <path fill="#1976D2" d="M43.611 20.083H42V20H24v8h11.303a12.05 12.05 0 0 1-4.084 5.57l.003-.002 6.19 5.238C36.971 39.214 44 34 44 24c0-1.341-.138-2.651-.389-3.917Z"/>
                              </svg>
                            </div>
                            <div>
                              <p class="text-base font-semibold text-white">Login with Google</p>
                              <p class="text-sm text-zinc-300">Sign in with Google</p>
                            </div>
                          </div>
                          <span class="text-2xl leading-none transition-transform duration-200 group-hover:translate-x-1">→</span>
                        </button>

                        <div class="flex items-center gap-4 py-1">
                          <div class="h-px flex-1 bg-[var(--color-border)]"></div>
                          <span class="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--color-text-muted)]">Coming soon</span>
                          <div class="h-px flex-1 bg-[var(--color-border)]"></div>
                        </div>

                        <div class="grid gap-3">
                          <button
                            v-for="provider in comingSoonProviders"
                            :key="provider.id"
                            disabled
                            class="flex w-full items-center justify-between rounded-[1.25rem] border border-zinc-200 bg-[var(--color-base)] px-4 py-4 text-left text-zinc-500 transition-colors disabled:cursor-not-allowed disabled:opacity-100"
                          >
                            <div class="flex items-center gap-4">
                              <div class="flex h-11 w-11 items-center justify-center rounded-full border border-white bg-white text-sm font-semibold text-[var(--color-text-main)] shadow-sm">
                                {{ provider.badge }}
                              </div>
                              <div>
                                <p class="text-sm font-semibold text-[var(--color-text-main)]">{{ provider.label }}</p>
                                <p class="text-sm text-[var(--color-text-muted)]">Coming soon</p>
                              </div>
                            </div>
                            <span class="rounded-full border border-zinc-200 bg-white px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--color-text-muted)]">
                              Disabled
                            </span>
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div class="mt-5 flex flex-col items-center justify-between gap-3 text-sm text-[var(--color-text-muted)] sm:flex-row">
                    <a
                      href="/terms-and-conditions.html"
                      @click.prevent="openTermsAndConditions"
                      class="transition-colors hover:text-[var(--color-text-main)]"
                    >
                      Terms of Service
                    </a>
                    <p class="text-center text-sm text-[var(--color-text-muted)]">Private desktop workspace for modern data analysis.</p>
                    <p class="text-sm text-[var(--color-text-muted)]">© 2026 Inquira</p>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </main>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useAuthStore } from '../../stores/authStore'
import { openExternalUrl } from '../../services/externalLinkService'
import { ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
import logo from '../../assets/favicon.svg'

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
  'Run notebook-style analysis without leaving the conversation.',
  'Keep datasets, tables, figures, and code in one workspace.',
  'Switch from quick questions to deep analysis without context loss.',
  'Stay desktop-native with local sessions that reconnect cleanly.',
]

const brandBullets = [
  {
    title: 'Ask and inspect',
    body: 'Move from natural language questions into code, tables, and charts without changing tools.',
  },
  {
    title: 'Stay grounded',
    body: 'The interface keeps the same calm palette and structure you already use in the main app.',
  },
  {
    title: 'Reconnect fast',
    body: 'Saved sessions restore directly into your workspace instead of making you start over.',
  },
]

const comingSoonProviders = [
  { id: 'microsoft', short: 'Microsoft', label: 'Login with Microsoft', badge: 'MS' },
  { id: 'github', short: 'GitHub', label: 'Login with GitHub', badge: 'GH' },
]

const progressBullets = [
  {
    title: 'One steady screen',
    body: 'The login shell stays mounted while the headline and supporting copy update with each startup stage.',
  },
  {
    title: 'Visible handoff',
    body: 'Browser sign-in, session verification, and workspace restore now read like one connected flow.',
  },
  {
    title: 'No hidden kernel work',
    body: 'When workspace runtime setup starts, the same screen keeps showing the next step instead of swapping to a detached dialog.',
  },
]

const progressConfig = computed(() => {
  const stage = String(authStore.authFlowStage || '').trim()
  const fallback = authStore.authFlowMessage || 'Preparing your Inquira session...'

  switch (stage) {
    case 'checking_session':
      return { percent: 12, title: 'Checking saved session', description: fallback }
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

const progressTitle = computed(() => progressConfig.value.title)
const progressDescription = computed(() => progressConfig.value.description)
const progressPercentLabel = computed(() => `${progressConfig.value.percent || 0}%`)
const displayMessage = computed(() => authStore.error || '')
const activeFeatureLine = computed(() => featureLines[featureIndex.value] || '')
const featureWidthCh = computed(() => Math.max(34, Math.min(80, activeFeatureLine.value.length + 2)))
const progressWidthCh = computed(() => Math.max(22, Math.min(48, (progressTitle.value || 'Preparing your workspace').length + 2)))
const heroPill = computed(() => (showProgressScreen.value ? 'Secure handoff in progress' : 'Desktop analytics workspace'))
const heroEyebrow = computed(() => (showProgressScreen.value ? 'Your workspace is being restored' : 'Your data, one workspace'))
const heroTitle = computed(() => {
  if (!showProgressScreen.value) return 'Think clearly, analyze faster.'
  return progressTitle.value || 'Preparing your workspace'
})
const heroDescription = computed(() => {
  if (!showProgressScreen.value) {
    return 'Inquira keeps chat, code, tables, and charts aligned in one calm, desktop-first workflow.'
  }
  return progressDescription.value || 'Inquira is finishing sign-in and restoring your workspace on this screen.'
})
const primaryPanelEyebrow = computed(() => (showProgressScreen.value ? 'Current handoff' : 'Why teams use it'))
const primaryPanelBadge = computed(() => (showProgressScreen.value ? 'NOW' : 'CE'))
const activeBrandBullets = computed(() => (showProgressScreen.value ? progressBullets : brandBullets))

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
  void openExternalUrl('https://docs.inquiraai.com/terms-of-service')
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
.auth-brand-panel {
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.9), rgba(253, 252, 248, 0.86)),
    linear-gradient(135deg, rgba(59, 130, 246, 0.05), rgba(24, 24, 27, 0.05));
}

.auth-grid {
  background-image:
    linear-gradient(rgba(228, 228, 231, 0.7) 1px, transparent 1px),
    linear-gradient(90deg, rgba(228, 228, 231, 0.7) 1px, transparent 1px);
  background-position: center;
  background-size: 34px 34px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.9), transparent 92%);
}

.auth-glow {
  background: radial-gradient(circle, rgba(59, 130, 246, 0.18), rgba(59, 130, 246, 0));
  filter: blur(10px);
}

.auth-glow-secondary {
  background: radial-gradient(circle, rgba(24, 24, 27, 0.12), rgba(24, 24, 27, 0));
}

.auth-spinner {
  width: 2.75rem;
  height: 2.75rem;
  border-radius: 9999px;
  border: 3px solid rgba(24, 24, 27, 0.1);
  border-top-color: #18181b;
  border-right-color: #3b82f6;
  animation: auth-spin 900ms linear infinite;
  flex-shrink: 0;
}

.auth-feature-type,
.auth-status-type {
  width: 0;
  overflow: hidden;
  white-space: nowrap;
  border-right: 2px solid rgba(39, 39, 42, 0.45);
  animation:
    auth-type 1.4s steps(28, end) forwards,
    auth-caret 0.9s step-end infinite;
}

@media (max-width: 640px) {
  .auth-feature-type,
  .auth-status-type {
    white-space: normal;
    width: 100%;
    border-right: 0;
    animation: none;
  }
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

@keyframes auth-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
