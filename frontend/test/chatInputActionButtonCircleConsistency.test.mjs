import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat input action button keeps one shared circular shell across mic, send, and stop states', () => {
  const componentPath = resolve(process.cwd(), 'src/components/chat/ChatInput.vue')
  const source = readFileSync(componentPath, 'utf-8')

  const sharedShell = 'class="flex w-6 h-6 items-center justify-center rounded-full bg-zinc-900 text-white"'
  const sharedShellMatches = source.match(new RegExp(sharedShell, 'g')) ?? []

  assert.equal(sharedShellMatches.length, 1)
  assert.equal(source.includes('<StopIcon v-if="appStore.isLoading" class="w-3 h-3" />'), true)
  assert.equal(source.includes('<MicrophoneIcon v-else-if="isComposerEmpty" class="w-3 h-3" />'), true)
  assert.equal(source.includes('<ArrowUpIcon v-else class="w-3 h-3" />'), true)
  assert.equal(source.includes('ArrowUpCircleIcon'), false)
  assert.equal(source.includes('StopCircleIcon'), false)
})
