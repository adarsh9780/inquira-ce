<template>
  <div class="flex flex-col h-full">
    <!-- Terminal Header -->
    <div class="flex-shrink-0 bg-gray-900 text-white px-4 py-3">
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-3">
          <CommandLineIcon class="h-5 w-5" />
          <h3 class="text-sm font-medium">Terminal Output</h3>
          <span v-if="appStore.terminalOutput" class="text-xs bg-gray-700 px-2 py-1 rounded">
            {{ outputType }}
          </span>
        </div>
        
        <div class="flex items-center space-x-2">
          <!-- Copy Output Button -->
          <button
            @click="copyOutput"
            :disabled="!appStore.terminalOutput"
            class="inline-flex items-center px-2 py-1 text-xs font-medium rounded text-gray-300 hover:text-white hover:bg-gray-700 transition-colors"
            :class="!appStore.terminalOutput ? 'opacity-50 cursor-not-allowed' : ''"
          >
            <DocumentDuplicateIcon class="h-3 w-3 mr-1" />
            Copy
          </button>
          
          <!-- Clear Terminal Button -->
          <button
            @click="clearTerminal"
            :disabled="!appStore.terminalOutput"
            class="inline-flex items-center px-2 py-1 text-xs font-medium rounded text-gray-300 hover:text-white hover:bg-gray-700 transition-colors"
            :class="!appStore.terminalOutput ? 'opacity-50 cursor-not-allowed' : ''"
          >
            <TrashIcon class="h-3 w-3 mr-1" />
            Clear
          </button>
        </div>
      </div>
    </div>
    
    <!-- Terminal Content -->
    <div class="flex-1 bg-gray-900 text-gray-100 overflow-hidden">
      <div v-if="formattedOutput" class="h-full overflow-y-auto">
        <pre class="p-4 text-sm font-mono leading-relaxed whitespace-pre-wrap">{{ formattedOutput }}</pre>
      </div>
      
      <!-- Empty State -->
      <div v-else class="h-full flex items-center justify-center">
        <div class="text-center text-gray-500">
          <CommandLineIcon class="h-12 w-12 mx-auto mb-3 text-gray-600" />
          <p class="text-sm">No output to display</p>
          <p class="text-xs text-gray-600 mt-1">Terminal output will appear here</p>
        </div>
      </div>
    </div>
    
    <!-- Terminal Footer with Status -->
    <div class="flex-shrink-0 bg-gray-800 text-gray-300 px-4 py-2 text-xs">
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-4">
          <span class="flex items-center space-x-1">
            <div 
              class="w-2 h-2 rounded-full"
              :class="statusIndicatorClass"
            />
            <span>{{ statusText }}</span>
          </span>
          <span v-if="formattedOutput">
            {{ lineCount }} lines
          </span>
        </div>
        
        <div class="flex items-center space-x-2">
          <span>{{ currentTime }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '../../stores/appStore'
import { 
  CommandLineIcon, 
  DocumentDuplicateIcon, 
  TrashIcon 
} from '@heroicons/vue/24/outline'

const appStore = useAppStore()

const currentTime = ref('')
let timeInterval = null

const formattedOutput = computed(() => {
  let output = appStore.terminalOutput || ''

  // Add scalars if available
  if (appStore.scalars && appStore.scalars.length > 0) {
    const scalarsDict = {}
    appStore.scalars.forEach((scalar) => {
      if (scalar && scalar.name) {
        scalarsDict[scalar.name] = scalar.value
      }
    })

    const scalarsText = `\n\nScalars:\n${JSON.stringify(scalarsDict, null, 2)}`
    output += scalarsText
  }

  if (!output) return ''

  // Add timestamp prefix to each line
  const timestamp = new Date().toLocaleTimeString()
  const lines = output.split('\n')

  return lines.map((line, index) => {
    if (index === 0) {
      return `[${timestamp}] ${line}`
    }
    return line
  }).join('\n')
})

const lineCount = computed(() => {
  const output = formattedOutput.value
  if (!output) return 0
  return output.split('\n').length
})

const outputType = computed(() => {
  const output = formattedOutput.value
  if (!output) return ''

  const lowerOutput = output.toLowerCase()
  if (lowerOutput.includes('error') || lowerOutput.includes('exception') || lowerOutput.includes('traceback')) {
    return 'Error'
  } else if (lowerOutput.includes('warning')) {
    return 'Warning'
  } else if (lowerOutput.includes('success') || lowerOutput.includes('completed')) {
    return 'Success'
  }
  return 'Output'
})

const statusIndicatorClass = computed(() => {
  if (appStore.isCodeRunning) {
    return 'bg-orange-500'
  }
  switch (outputType.value) {
    case 'Error':
      return 'bg-red-500'
    case 'Warning':
      return 'bg-yellow-500'
    case 'Success':
      return 'bg-green-500'
    default:
      return 'bg-blue-500'
  }
})

const statusText = computed(() => {
  if (appStore.isCodeRunning) {
    return 'Processing'
  }
  if (!formattedOutput.value) {
    return 'Ready'
  }
  return `${outputType.value} - Last updated ${new Date().toLocaleTimeString()}`
})

onMounted(() => {
  updateTime()
  timeInterval = setInterval(updateTime, 1000)
})

onUnmounted(() => {
  if (timeInterval) {
    clearInterval(timeInterval)
  }
})

function updateTime() {
  currentTime.value = new Date().toLocaleTimeString()
}

async function copyOutput() {
  if (!formattedOutput.value) return

  try {
    await navigator.clipboard.writeText(formattedOutput.value)
    console.log('Terminal output copied to clipboard')
    // You could add a toast notification here
  } catch (error) {
    console.error('Failed to copy terminal output:', error)
  }
}

function clearTerminal() {
  if (confirm('Are you sure you want to clear the terminal output?')) {
    appStore.setTerminalOutput('')
    appStore.setScalars([])
  }
}
</script>

<style scoped>
/* Terminal-specific styling */
pre {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
}

/* Custom scrollbar for terminal */
.overflow-y-auto::-webkit-scrollbar {
  width: 8px;
}

.overflow-y-auto::-webkit-scrollbar-track {
  background: #374151;
}

.overflow-y-auto::-webkit-scrollbar-thumb {
  background: #6b7280;
  border-radius: 4px;
}

.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}
</style>