<template>
  <!-- Modal Overlay -->
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 overflow-y-auto"
    aria-labelledby="modal-title"
    role="dialog"
    aria-modal="true"
  >
    <!-- Background overlay -->
    <div
      class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
      @click="closeModal"
    ></div>

    <!-- Modal container -->
    <div class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
      <div
        class="relative transform overflow-hidden rounded-lg bg-white text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-2xl"
        @click.stop
      >
        <!-- Modal Header -->
        <div class="bg-white px-6 py-4 border-b border-gray-200">
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold text-gray-900" id="modal-title">
              Keyboard Shortcuts
            </h3>
            <button
              @click="closeModal"
              class="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <XMarkIcon class="h-6 w-6" />
            </button>
          </div>
        </div>

        <!-- Modal Body -->
        <div class="bg-white px-6 py-6 max-h-96 overflow-y-auto">
          <div class="space-y-6">
            <!-- Shortcut Mode System -->
            <div>
              <h4 class="text-md font-semibold text-gray-900 mb-3 flex items-center">
                <CommandLineIcon class="h-5 w-5 mr-2 text-blue-600" />
                Single-Letter Shortcuts
              </h4>
              <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                <div class="flex items-start">
                  <div class="flex-shrink-0">
                    <kbd class="px-3 py-2 text-sm font-bold text-blue-800 bg-blue-200 rounded-lg border border-blue-300">
                      Single Keys
                    </kbd>
                    <span class="text-xs text-blue-600 block mt-1">(No modifiers)</span>
                  </div>
                  <div class="ml-4">
                    <h5 class="text-sm font-medium text-blue-900 mb-1">Ultra-Simple Shortcuts</h5>
                    <p class="text-sm text-blue-800 mb-2"><strong>Method:</strong> Just press the single letter key</p>
                    <p class="text-sm text-blue-800"><strong>Smart:</strong> Only works when not typing in input fields</p>
                  </div>
                </div>
              </div>

              <!-- Panel Navigation -->
              <div class="bg-gray-50 rounded-lg p-4 mb-4">
                <h5 class="text-sm font-medium text-gray-900 mb-3">Panel Navigation</h5>
                <div class="grid grid-cols-2 gap-3">
                  <div class="flex items-center justify-between py-2">
                    <span class="text-sm text-gray-700">Code Tab</span>
                    <kbd class="px-2 py-1 text-xs font-semibold text-gray-800 bg-gray-200 rounded">c</kbd>
                  </div>
                  <div class="flex items-center justify-between py-2">
                    <span class="text-sm text-gray-700">Table Tab</span>
                    <kbd class="px-2 py-1 text-xs font-semibold text-gray-800 bg-gray-200 rounded">t</kbd>
                  </div>
                  <div class="flex items-center justify-between py-2">
                    <span class="text-sm text-gray-700">Figure Tab</span>
                    <kbd class="px-2 py-1 text-xs font-semibold text-gray-800 bg-gray-200 rounded">f</kbd>
                  </div>
                  <div class="flex items-center justify-between py-2">
                    <span class="text-sm text-gray-700">Console Tab</span>
                    <kbd class="px-2 py-1 text-xs font-semibold text-gray-800 bg-gray-200 rounded">o</kbd>
                  </div>
                </div>
              </div>

              <!-- Actions -->
              <div class="bg-gray-50 rounded-lg p-4 mb-4">
                <h5 class="text-sm font-medium text-gray-900 mb-3">Actions</h5>
                <div class="grid grid-cols-2 gap-3">
                  <div class="flex items-center justify-between py-2">
                    <span class="text-sm text-gray-700">Focus Chat</span>
                    <kbd class="px-2 py-1 text-xs font-semibold text-gray-800 bg-gray-200 rounded">i</kbd>
                  </div>
                  <div class="flex items-center justify-between py-2">
                    <span class="text-sm text-gray-700">Focus Code (End)</span>
                    <kbd class="px-2 py-1 text-xs font-semibold text-gray-800 bg-gray-200 rounded">w</kbd>
                  </div>
                  <div class="flex items-center justify-between py-2">
                    <span class="text-sm text-gray-700">Run Code</span>
                    <kbd class="px-2 py-1 text-xs font-semibold text-gray-800 bg-gray-200 rounded">r</kbd>
                  </div>
                  <div class="flex items-center justify-between py-2">
                    <span class="text-sm text-gray-700">Download Code</span>
                    <kbd class="px-2 py-1 text-xs font-semibold text-gray-800 bg-gray-200 rounded">g</kbd>
                  </div>
                  <div class="flex items-center justify-between py-2">
                    <span class="text-sm text-gray-700">Open Preview</span>
                    <kbd class="px-2 py-1 text-xs font-semibold text-gray-800 bg-gray-200 rounded">p</kbd>
                  </div>
                  <div class="flex items-center justify-between py-2">
                    <span class="text-sm text-gray-700">Open Settings</span>
                    <kbd class="px-2 py-1 text-xs font-semibold text-gray-800 bg-gray-200 rounded">,</kbd>
                  </div>
                  <div class="flex items-center justify-between py-2">
                    <span class="text-sm text-gray-700">Open Shortcuts</span>
                    <kbd class="px-2 py-1 text-xs font-semibold text-gray-800 bg-gray-200 rounded">k</kbd>
                  </div>
                  <div class="flex items-center justify-between py-2">
                    <span class="text-sm text-gray-700">Preview Data Tab</span>
                    <kbd class="px-2 py-1 text-xs font-semibold text-gray-800 bg-gray-200 rounded">d</kbd>
                  </div>
                </div>
              </div>

              <!-- Preview Navigation -->
              <div class="bg-gray-50 rounded-lg p-4">
                <h5 class="text-sm font-medium text-gray-900 mb-3">Preview Shortcuts</h5>
                <div class="grid grid-cols-1 gap-3">
                  <div class="flex items-center justify-between py-2">
                    <span class="text-sm text-gray-700">Open Preview (Schema)</span>
                    <kbd class="px-2 py-1 text-xs font-semibold text-gray-800 bg-gray-200 rounded">p</kbd>
                  </div>
                  <div class="flex items-center justify-between py-2">
                    <span class="text-sm text-gray-700">Open Preview (Data)</span>
                    <kbd class="px-2 py-1 text-xs font-semibold text-gray-800 bg-gray-200 rounded">d</kbd>
                  </div>
                  <div class="flex items-center justify-between py-2">
                    <span class="text-sm text-gray-700">Open Preview (Schema)</span>
                    <kbd class="px-2 py-1 text-xs font-semibold text-gray-800 bg-gray-200 rounded">s</kbd>
                  </div>
                </div>
              </div>
            </div>

            <!-- Tips -->
            <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div class="flex items-start">
                <LightBulbIcon class="h-5 w-5 text-blue-600 mr-3 mt-0.5" />
                <div>
                  <h5 class="text-sm font-medium text-blue-900 mb-2">Tips</h5>
                  <ul class="text-sm text-blue-800 space-y-1">
                    <li>• <strong>How to use shortcuts:</strong></li>
                    <li class="ml-4">• Just press the <strong>single letter</strong> when not in input fields</li>
                    <li class="ml-4">• No modifier keys needed!</li>
                    <li>• <strong>Smart detection:</strong> Only works when not typing</li>
                    <li>• <strong>Cross-platform:</strong> Works on Windows, Mac, and Linux</li>
                    <li>• <strong>Escape to exit:</strong> Press Escape to leave input fields</li>
                    <li>• <strong>w</strong> focuses code editor at end of line</li>
                    <li>• <strong>r</strong> runs the Python code</li>
                    <li>• <strong>g</strong> downloads the Python code file</li>
                    <li>• <strong>p/d/s</strong> open preview with different default tabs</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Modal Footer -->
        <div class="bg-gray-50 px-6 py-4 flex justify-between items-center">
          <div class="flex items-center">
            <input
              id="dont-show-again"
              type="checkbox"
              v-model="dontShowAgain"
              class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <label for="dont-show-again" class="ml-2 text-sm text-gray-700">
              Don't show this again
            </label>
          </div>
          <button
            @click="closeModal"
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useAppStore } from '../../stores/appStore'
import { XMarkIcon, CommandLineIcon, RectangleStackIcon, EyeIcon, LightBulbIcon } from '@heroicons/vue/24/outline'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close'])
const appStore = useAppStore()

const dontShowAgain = ref(false)

watch(() => props.isOpen, (open) => {
  if (open) {
    dontShowAgain.value = !!appStore.hideShortcutsModal
  }
})

function savePreference() {
  appStore.setHideShortcutsModal(dontShowAgain.value)
}

function closeModal() {
  savePreference()
  emit('close')
}

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && props.isOpen) {
    closeModal()
  }
})
</script>

<style scoped>
/* Custom styling for keyboard shortcuts */
kbd {
  font-family: monospace;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}
</style>
