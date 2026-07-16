import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('status bar exposes session notification center with bell trigger', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/StatusBar.vue'), 'utf-8')

  assert.equal(source.includes('data-notification-center'), true)
  assert.equal(source.includes('Session Notifications'), true)
  assert.equal(source.includes('Stored for this app session only.'), true)
  assert.equal(source.includes('BellIcon'), true)
  assert.equal(source.includes('unreadNotificationCount'), true)
  assert.equal(source.includes('markAllNotificationsRead()'), true)
  assert.equal(source.includes('clearNotificationHistory'), true)
  assert.equal(source.includes('notificationDotClass(entry.type)'), true)
})
