<template>
  <div class="flex flex-col h-full bg-white rounded-xl overflow-hidden">
    <!-- Chat History -->
    <div class="flex-1 overflow-y-auto bg-gray-50/30" data-chat-scroll-container>
      <div v-if="appStore.chatHistory.length === 0" class="flex items-center justify-center h-full px-4 sm:px-6 lg:px-8 pt-4 sm:pt-6 lg:pt-8 pb-2 sm:pb-3 lg:pb-4">
        <div class="text-center max-w-md">
          <div class="mx-auto flex items-center justify-center h-16 w-16 sm:h-20 sm:w-20 rounded-2xl bg-gradient-to-br from-blue-100 to-indigo-100 mb-4 sm:mb-6 shadow-lg">
            <ChatBubbleLeftRightIcon class="h-8 w-8 sm:h-10 sm:w-10 text-blue-600" />
          </div>
          <h3 class="text-xl sm:text-2xl font-bold text-gray-900 mb-2 sm:mb-3">Start Your Analysis</h3>
          <p class="text-sm sm:text-base text-gray-600 leading-relaxed">
            Point Inquira at your local dataset path, add your Gemini API key in Settings, then ask a question to generate code and insights.
          </p>
        </div>
      </div>

      <div v-else class="px-3 sm:px-4 pt-3 sm:pt-4 pb-2 sm:pb-3 space-y-3 sm:space-y-4">
        <ChatHistory />
      </div>
    </div>

    <!-- Chat Input -->
    <div class="flex-shrink-0 border-t border-gray-100 bg-white pt-2 sm:pt-3">
      <ChatInput />
    </div>
  </div>
</template>

<script setup>
import { useAppStore } from '../../stores/appStore'
import ChatHistory from './ChatHistory.vue'
import ChatInput from './ChatInput.vue'
import { ChatBubbleLeftRightIcon } from '@heroicons/vue/24/outline'

const appStore = useAppStore()
</script>
