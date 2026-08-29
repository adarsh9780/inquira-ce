<template>
  <section class="mx-auto max-w-2xl space-y-6">
    <div class="settings-card glass-panel">
      <div class="settings-card-header">
        <div>
          <h3 class="settings-card-title">Global proxy and trust</h3>
          <p class="mt-1 text-xs leading-5 text-[var(--color-text-muted)]">Used by every AI provider unless that provider has its own override.</p>
        </div>
      </div>
      <div class="settings-card-body space-y-4">
        <label class="input-group">
          <span class="input-label">Connection policy</span>
          <HeaderDropdown
            :model-value="settings.mode"
            :options="modeOptions"
            max-width-class="w-full"
            aria-label="Global proxy policy"
            @update:model-value="settings.mode = String($event || 'system')"
          />
        </label>

        <template v-if="settings.mode === 'custom'">
          <label class="input-group">
            <span class="input-label">Proxy URL</span>
            <input v-model="settings.proxy_url" type="url" class="text-input font-mono" placeholder="http://proxy.company:8080" autocomplete="off" spellcheck="false" />
            <span class="input-hint">HTTP and HTTPS proxy URLs are supported. Credentials remain visible so the value can be reviewed before saving.</span>
          </label>
          <label class="input-group">
            <span class="input-label">Bypass proxy for</span>
            <input v-model="settings.no_proxy" type="text" class="text-input font-mono" placeholder="localhost,.company.internal,10.0.0.0/8" autocomplete="off" spellcheck="false" />
            <span class="input-hint">Comma-separated hosts, domain suffixes, IP addresses, or CIDR ranges.</span>
          </label>
        </template>

        <label class="input-group">
          <span class="input-label">CA certificate bundle</span>
          <span class="flex gap-2">
            <input v-model="settings.ca_bundle_path" type="text" class="text-input min-w-0 flex-1 font-mono" placeholder="Optional company PEM certificate bundle" autocomplete="off" spellcheck="false" />
            <button type="button" class="btn-secondary px-3 py-1.5 text-xs" :disabled="loading" @click="chooseCertificate">Browse</button>
          </span>
          <span class="input-hint">Uses your organization’s root certificates for provider HTTPS connections without changing the operating-system trust store.</span>
        </label>
      </div>
    </div>

    <p v-if="errorMessage" class="rounded-lg bg-[var(--color-danger-bg)] px-3 py-2 text-xs text-[var(--color-danger-text)]" role="alert">{{ errorMessage }}</p>

    <div class="flex justify-end border-t border-[var(--color-border)] pt-4">
      <button type="button" class="btn-primary px-4 py-2 text-sm" :disabled="loading" @click="save">
        <span v-if="loading" class="inline-flex items-center gap-2"><span class="loading-spinner accent-spinner"></span>Saving…</span>
        <span v-else>Save network settings</span>
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import HeaderDropdown from '../../ui/HeaderDropdown.vue'
import { networkSettingsService } from '../../../services/networkSettingsService'
import { extractApiErrorMessage } from '../../../utils/apiError'
import { toast } from '../../../composables/useToast'

const modeOptions = [
  { value: 'system', label: 'Use operating-system proxy' },
  { value: 'custom', label: 'Use custom proxy' },
  { value: 'direct', label: 'Connect directly' },
]

const settings = reactive({
  mode: 'system',
  proxy_url: '',
  no_proxy: '',
  ca_bundle_path: '',
})
const loading = ref(false)
const errorMessage = ref('')

onMounted(load)

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await networkSettingsService.get() as Record<string, any>
    const global = response?.global || {}
    settings.mode = String(global.mode || 'system')
    settings.proxy_url = String(global.proxy_url || '')
    settings.no_proxy = String(global.no_proxy || '')
    settings.ca_bundle_path = String(global.ca_bundle_path || '')
  } catch (error) {
    errorMessage.value = extractApiErrorMessage(error, 'Could not load network settings.')
  } finally {
    loading.value = false
  }
}

async function chooseCertificate() {
  try {
    const selected = await networkSettingsService.chooseCertificate()
    if (selected) settings.ca_bundle_path = String(selected)
  } catch (error) {
    errorMessage.value = extractApiErrorMessage(error, 'Could not choose a certificate bundle.')
  }
}

async function save() {
  loading.value = true
  errorMessage.value = ''
  try {
    await networkSettingsService.save({ ...settings })
    toast.success('Network settings saved', 'AI provider calls now use the selected connection policy.')
  } catch (error) {
    errorMessage.value = extractApiErrorMessage(error, 'Could not save network settings.')
  } finally {
    loading.value = false
  }
}
</script>
